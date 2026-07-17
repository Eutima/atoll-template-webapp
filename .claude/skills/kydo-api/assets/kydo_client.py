"""Generischer, kopierbarer HTTP-Client für die Kydo-API, auf httpx portiert
(kein Django/requests nötig) — einsatzbereit in jedem Python-Projekt.

Der zentrale `_request()`-Wrapper setzt `Authorization: Bearer ...` und den
Query-Parameter `org_id` bei JEDEM Aufruf zwingend (siehe
references/api-quirks.md, Punkt 1) — kein Call-Site kann das vergessen.

Bekannte Abweichungen zwischen Spezifikation/OpenAPI-Doku und der realen
API sind in references/api-quirks.md dokumentiert; die jeweiligen Stellen
im Code verweisen darauf. Bei Unklarheiten dort zuerst nachsehen, bevor man
sich auf die offizielle Doku verlässt.
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterator, Optional

import httpx
from pydantic import BaseModel, field_validator

RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


class KydoApiError(Exception):
    """Fehler bei einem Aufruf der Kydo-API (Timeout, Auth-Fehler, 5xx nach Retries)."""


# --- Pydantic-Modelle für die relevanten Kydo-API-Schemas ------------------
# 1:1 an reale Beispiel-Payloads angelehnt, nicht an die (teils falsche)
# Spezifikation — siehe references/api-quirks.md.


class KydoTax(BaseModel):
    id: int
    code: str
    value: float
    bexio_id: Optional[str] = None
    account_no: Optional[str] = None
    display_name: Optional[str] = None


class KydoCurrency(BaseModel):
    name: str
    bexio_id: Optional[str] = None
    round_factor: Optional[float] = None
    md: Optional[dict] = None


class KydoBookingRow(BaseModel):
    id: int
    org_id: int
    booking_date: str
    debit_account_no: str
    credit_account_no: str
    description: str = ""
    tax: Optional[KydoTax] = None
    currency: Optional[KydoCurrency] = None
    amount_incl_tax: float
    amount_incl_tax_chf: Optional[float] = None
    exchange_rate: Optional[float] = 1.0
    cost_center_debit: Optional[str] = None
    cost_type_debit: Optional[str] = None
    cost_center_credit: Optional[str] = None
    cost_type_credit: Optional[str] = None
    external_reference: Optional[str] = None
    data: Optional[dict] = None
    locked: bool = False
    is_manual: bool = False
    document: Optional[int] = None
    bank_transaction: Optional[int] = None

    @field_validator("tax", mode="before")
    @classmethod
    def _leeren_steuercode_als_none_behandeln(cls, value: Any) -> Any:
        """Siehe api-quirks.md Punkt 4: `tax` kommt real als `""`, `{}` oder
        `null` — alle drei bedeuten "kein Steuercode"."""
        return None if value in ("", {}) else value


class KydoAttribute(BaseModel):
    """Siehe api-quirks.md Punkt 9: reale Schlüssel sind `format`/`isunique`,
    nicht `type`/`unique` wie ältere Spezifikationen annahmen."""

    name: str
    format: Optional[str] = None
    default_value: Optional[Any] = None
    order: Optional[int] = None
    required: bool = False
    hidden: bool = False
    isunique: bool = False
    isreference: Optional[int] = None
    reference_metadata: Optional[dict] = None


class KydoDocType(BaseModel):
    """`GET /v1/docType/doc_type/{id_or_name}/` für einen einzelnen (inkl.
    Attribute), `GET /v1/docType/doc_type/` für alle (OHNE Attribute, siehe
    api-quirks.md Punkt 8)."""

    id: Optional[int] = None
    name: str
    attributes: list[KydoAttribute] = []


class KydoAttachment(BaseModel):
    id: Optional[int] = None
    uuid: Optional[str] = None
    url: Optional[str] = None


class KydoAccount(BaseModel):
    """Konto aus dem Kydo-Kontenplan (`GET /v1/finac/accounting_plan/`,
    verschachtelt unter `accounts`, siehe api-quirks.md Punkt 5). Mehrere
    Felder sind bewusst optional UND können `None` sein: reine Gruppen-/
    Kopfzeilen liefern `id`, `is_active`, `is_locked`, `account_type` als
    `null` (Punkt 6). `account_type` ist zudem in der Praxis oft für
    sämtliche Konten durchgängig `null` (Punkt 7) — für eine Klassifizierung
    nicht darauf verlassen, stattdessen auf die Kontonummer zurückfallen."""

    id: Optional[int] = None
    name: str
    uuid: Optional[str] = None
    tax_id: Optional[int] = None
    is_active: Optional[bool] = True
    is_locked: Optional[bool] = False
    account_no: str
    account_type: Optional[int] = None
    fibu_account_group_id: Optional[int] = None
    fibu_account_group_name: Optional[str] = None


# --- Client -----------------------------------------------------------


class KydoClient:
    """httpx-basierter Kydo-API-Client. Framework-agnostisch — kein Django,
    keine App-spezifischen Modelle. `org_id` und der Bearer-Token werden im
    Konstruktor einmal gesetzt und danach bei JEDEM Request automatisch
    mitgeschickt (api-quirks.md Punkt 1)."""

    def __init__(
        self,
        base_url: str,
        org_id: int,
        bearer_token: str,
        timeout: float = 15,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.org_id = org_id
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {bearer_token}"},
            timeout=timeout,
        )

    @classmethod
    def from_env(cls, prefix: str = "KYDO_") -> "KydoClient":
        """Baut einen Client aus Umgebungsvariablen `{prefix}BASE_URL`,
        `{prefix}ORG_ID`, `{prefix}BEARER_TOKEN`. Bequemlichkeit für
        Skripte/Standalone-Nutzung; in Anwendungen mit eigener
        Verbindungs-/Settings-Quelle stattdessen direkt konstruieren."""
        return cls(
            base_url=os.environ[f"{prefix}BASE_URL"],
            org_id=int(os.environ[f"{prefix}ORG_ID"]),
            bearer_token=os.environ[f"{prefix}BEARER_TOKEN"],
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "KydoClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _request(self, method: str, path: str, params: Optional[dict] = None, **kwargs: Any) -> httpx.Response:
        params = dict(params or {})
        params["org_id"] = self.org_id  # zwingend bei JEDEM Aufruf, siehe api-quirks.md Punkt 1

        attempt = 0
        while True:
            try:
                response = self.client.request(method, path, params=params, **kwargs)
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    attempt += 1
                    time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                    continue
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise KydoApiError(f"Kydo-API-Aufruf fehlgeschlagen ({method} {path}): {exc}") from exc
            except httpx.HTTPError as exc:
                if attempt < self.max_retries:
                    attempt += 1
                    time.sleep(self.backoff_factor * (2 ** (attempt - 1)))
                    continue
                raise KydoApiError(f"Kydo-API-Aufruf fehlgeschlagen ({method} {path}): {exc}") from exc
            return response

    def test_connection(self) -> tuple[bool, Optional[str]]:
        try:
            self._request("GET", "/v1/auth/config/")
            return True, None
        except KydoApiError as exc:
            return False, str(exc)

    def list_bookings(
        self,
        booking_date__gte: Optional[str] = None,
        locked: Optional[bool] = True,
        page_size: int = 100,
    ) -> Iterator[KydoBookingRow]:
        """Generator über alle Seiten von `GET /v1/cv/journal/` — NICHT
        `/v1/cv/bookings/` (liefert 404, siehe api-quirks.md Punkt 2)."""
        page = 1
        while True:
            params: dict[str, Any] = {"page": page, "page_size": page_size}
            if booking_date__gte is not None:
                params["booking_date__gte"] = booking_date__gte
            if locked is not None:
                params["locked"] = str(locked).lower()
            response = self._request("GET", "/v1/cv/journal/", params=params)
            payload = response.json()
            results = payload.get("results", payload if isinstance(payload, list) else [])
            for row in results:
                yield KydoBookingRow(**row)
            has_next = payload.get("next") if isinstance(payload, dict) else None
            if not has_next or not results:
                break
            page += 1

    def get_accounting_plan(self) -> list[KydoAccount]:
        """`GET /v1/finac/accounting_plan/` — nicht paginiert; Antwort
        verschachtelt die Konten unter `accounts` (api-quirks.md Punkt 5)."""
        response = self._request("GET", "/v1/finac/accounting_plan/")
        payload = response.json()
        return [KydoAccount(**row) for row in payload.get("accounts", [])]

    def get_document_attachments(self, document_id: int) -> list[dict[str, Any]]:
        """Achtung: die gelieferten URLs sind Bearer-Token-geschützt und
        NICHT für Browser-Links geeignet — siehe `build_document_link()`
        und api-quirks.md Punkt 11."""
        response = self._request("GET", f"/v1/docType/document/{document_id}/attachment/")
        payload = response.json()
        return payload if isinstance(payload, list) else payload.get("results", [])

    def list_doc_types(self) -> list[KydoDocType]:
        """`GET /v1/docType/doc_type/` — liefert ALLE Dokumenttypen OHNE
        Attribute (api-quirks.md Punkt 8); für Attribute `get_doc_type()`."""
        response = self._request("GET", "/v1/docType/doc_type/")
        payload = response.json()
        results = payload if isinstance(payload, list) else payload.get("results", [])
        return [KydoDocType(**row) for row in results]

    def get_doc_type(self, id_or_name: int | str) -> KydoDocType:
        response = self._request("GET", f"/v1/docType/doc_type/{id_or_name}/")
        return KydoDocType(**response.json())

    def upload_file(self, file_obj: Any, file_name: str, doctype_name: str) -> str:
        """Schritt 1 des Beleg-Uploads (siehe SKILL.md). Liefert die `uuid`
        des hochgeladenen Attachments."""
        response = self._request(
            "POST",
            "/v1/upload/file/",
            data={"doctype": doctype_name},
            files={"file": (file_name, file_obj)},
        )
        return response.json()["uuid"]

    def create_document(self, doc_type_name: str, attributes: dict[str, Any]) -> int:
        """Schritt 2 des Beleg-Uploads. Liefert die `document_id` DIREKT in
        der Response (api-quirks.md Punkt 10b)."""
        response = self._request("POST", f"/v1/docType/document/{doc_type_name}/", json=attributes)
        return response.json()["id"]

    def link_attachment_to_document(self, document_id: int, attachment_uuid: str) -> dict[str, Any]:
        """Schritt 3 des Beleg-Uploads. Pfad endet bewusst OHNE `/upload`
        (api-quirks.md Punkt 10c)."""
        response = self._request(
            "POST",
            f"/v1/docType/document/{document_id}/attachment/",
            json={"attachment_uuid": attachment_uuid},
        )
        return response.json()

    def upload_document(
        self,
        file_obj: Any,
        file_name: str,
        doc_type_name: str,
        attributes: dict[str, Any],
    ) -> tuple[int, str]:
        """Führt den kompletten 3-Schritt-Ablauf aus und liefert
        `(document_id, attachment_uuid)`. Convenience-Wrapper, falls kein
        Zwischenzustand zwischen den einzelnen Schritten benötigt wird."""
        attachment_uuid = self.upload_file(file_obj, file_name, doc_type_name)
        document_id = self.create_document(doc_type_name, attributes)
        self.link_attachment_to_document(document_id, attachment_uuid)
        return document_id, attachment_uuid


def build_document_link(web_base_url: str, org_id: int, document_id: Optional[int]) -> str:
    """Baut den im Browser aufrufbaren Kydo-Weboberflächen-Link zu einem
    Dokument. NICHT die von `get_document_attachments()` gelieferte
    Attachment-URL verwenden — die zeigt auf die API und ist
    Bearer-Token-geschützt (api-quirks.md Punkt 11)."""
    if document_id is None:
        return ""
    return f"{web_base_url.rstrip('/')}/search/{document_id}?org_id={org_id}"
