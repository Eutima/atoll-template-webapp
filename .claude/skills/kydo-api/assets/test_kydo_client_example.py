"""Test-Mocking-Vorlage für KydoClient (httpx-Variante). Kopierbar als
Ausgangspunkt für projekteigene Tests — zeigt, wie man `httpx.Client` ohne
echte Netzwerkaufrufe testet (via `httpx.MockTransport`) und deckt dabei
die dokumentierten API-Quirks aus references/api-quirks.md als
Regressionstests ab. Passe den Import unten an den tatsächlichen Pfad an,
unter dem `kydo_client.py` im Zielprojekt liegt.
"""

import httpx
import pytest

from kydo_client import KydoApiError, KydoClient, build_document_link


def _client_with_transport(handler):
    client = KydoClient(base_url="https://api.kydo.example", org_id=42, bearer_token="tok")
    client.client = httpx.Client(
        base_url=client.base_url,
        headers=client.client.headers,
        transport=httpx.MockTransport(handler),
    )
    return client


def test_org_id_always_included_in_request_params():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["org_id"] = request.url.params.get("org_id")
        return httpx.Response(200, json={"results": []})

    client = _client_with_transport(handler)
    client._request("GET", "/v1/cv/journal/", params={"page": 1})

    assert captured["org_id"] == "42"


def test_request_error_wrapped_as_kydo_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client = _client_with_transport(handler)
    client.max_retries = 0  # keine Retry-Wartezeit im Test
    with pytest.raises(KydoApiError):
        client._request("GET", "/v1/auth/config/")


def test_test_connection_returns_false_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    client = _client_with_transport(handler)
    client.max_retries = 0
    ok, fehler = client.test_connection()
    assert ok is False
    assert fehler is not None


def test_test_connection_returns_true_on_success():
    client = _client_with_transport(lambda request: httpx.Response(200, json={}))
    ok, fehler = client.test_connection()
    assert ok is True
    assert fehler is None


def test_list_bookings_paginates_until_no_next():
    fake_booking = {
        "id": 1,
        "org_id": 42,
        "booking_date": "2026-01-01",
        "debit_account_no": "1000",
        "credit_account_no": "2000",
        "amount_incl_tax": 10.0,
    }
    responses = [
        httpx.Response(200, json={"results": [fake_booking], "next": "page2"}),
        httpx.Response(200, json={"results": [], "next": None}),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    client = _client_with_transport(handler)
    results = list(client.list_bookings())

    assert len(results) == 1
    assert results[0].id == 1


def test_list_bookings_calls_journal_endpoint_not_bookings():
    """Regressionstest: `/v1/cv/bookings/` liefert gegen die reale API einen
    404 — der tatsächlich funktionierende Pfad ist `/v1/cv/journal/`
    (api-quirks.md Punkt 2)."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json={"results": [], "next": None})

    client = _client_with_transport(handler)
    list(client.list_bookings())

    assert captured["path"].endswith("/v1/cv/journal/")


def test_list_bookings_tolerates_empty_tax_variants():
    """Regressionstest: `tax` kommt real als `""` oder `{}` statt `null` —
    beides muss als "kein Steuercode" behandelt werden (api-quirks.md
    Punkt 4)."""
    zeile_leere_zeichenkette = {
        "id": 37652,
        "org_id": 92306,
        "booking_date": "2026-06-26",
        "debit_account_no": "2457",
        "credit_account_no": "1020",
        "description": "Rückzahlung Darlehen",
        "tax": "",
        "currency": {"name": "CHF"},
        "amount_incl_tax": 10000.0,
    }
    zeile_leeres_dict = {**zeile_leere_zeichenkette, "id": 37176, "tax": {}}
    payload = {"results": [zeile_leere_zeichenkette, zeile_leeres_dict], "next": None}

    client = _client_with_transport(lambda request: httpx.Response(200, json=payload))
    result = list(client.list_bookings())

    assert len(result) == 2
    assert result[0].tax is None
    assert result[1].tax is None


def test_upload_file_returns_uuid():
    client = _client_with_transport(lambda request: httpx.Response(200, json={"uuid": "abc-123"}))
    result = client.upload_file(b"data", "test.pdf", "creditor")
    assert result == "abc-123"


def test_create_document_returns_id_directly_from_response():
    """Regressionstest: `document_id` kommt direkt in der Response (Feld
    `id`), entgegen mancher älterer OpenAPI-Doku, die "kein Response-Body"
    behauptet (api-quirks.md Punkt 10b)."""
    client = _client_with_transport(lambda request: httpx.Response(200, json={"id": 555}))
    result = client.create_document("creditor", {"text": "hi"})
    assert result == 555


def test_link_attachment_to_document_posts_correct_payload_without_upload_suffix():
    """Regressionstest: der Pfad endet OHNE `/upload` (api-quirks.md Punkt
    10c) — das Suffix gehört zu einem anderen Endpunkt (neue Dateiversion an
    einem bestehenden Dokument)."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, json={"id": 1, "url": "https://x"})

    client = _client_with_transport(handler)
    client.link_attachment_to_document(555, "attach-uuid")

    assert captured["path"].endswith("/v1/docType/document/555/attachment/")
    assert not captured["path"].endswith("/upload/")


def test_get_document_attachments_returns_list():
    client = _client_with_transport(lambda request: httpx.Response(200, json=[{"url": "https://x"}]))
    result = client.get_document_attachments(555)
    assert result == [{"url": "https://x"}]


def test_get_accounting_plan_parses_nested_accounts_key():
    """Regressionstest: die Konten stecken unter `accounts`, nicht als
    bare Liste (api-quirks.md Punkt 5)."""
    payload = {
        "id": 0,
        "accounts": [
            {
                "id": 89,
                "name": "Saldoübernahme",
                "uuid": "6f04e629-2882-4181-b006-9b3221bc7138",
                "tax_id": None,
                "is_active": True,
                "is_locked": True,
                "account_no": "9901",
                "account_type": 5,
                "fibu_account_group_id": 68,
                "fibu_account_group_name": "Abschluss",
            }
        ],
        "application": 0,
        "org_id": 0,
    }
    client = _client_with_transport(lambda request: httpx.Response(200, json=payload))
    result = client.get_accounting_plan()

    assert len(result) == 1
    assert result[0].account_no == "9901"
    assert result[0].fibu_account_group_name == "Abschluss"


def test_get_accounting_plan_tolerates_null_fields_on_group_rows():
    """Regressionstest: reine Gruppen-/Kopfzeilen liefern `id`, `is_active`,
    `is_locked`, `account_type` als `null` (api-quirks.md Punkt 6) — darf
    keinen ValidationError auslösen."""
    payload = {
        "id": 0,
        "accounts": [
            {
                "id": None,
                "name": "Abschluss",
                "uuid": None,
                "tax_id": None,
                "is_active": None,
                "is_locked": None,
                "account_no": "9",
                "account_type": None,
                "fibu_account_group_id": None,
                "fibu_account_group_name": None,
            }
        ],
        "application": 0,
        "org_id": 0,
    }
    client = _client_with_transport(lambda request: httpx.Response(200, json=payload))
    result = client.get_accounting_plan()

    assert result[0].id is None
    assert result[0].account_type is None
    assert result[0].account_no == "9"


def test_list_doc_types_parses_flat_list_without_attributes():
    """Regressionstest: liefert eine flache Liste OHNE Attribute
    (api-quirks.md Punkt 8) — die kommen erst über `get_doc_type()`."""
    payload = [
        {"id": 7346, "name": "belege_jahresabschluss", "tags": []},
        {"id": 7580, "name": "creditor", "tags": ["cv-expenses-creditor"]},
    ]
    client = _client_with_transport(lambda request: httpx.Response(200, json=payload))
    result = client.list_doc_types()

    assert [d.name for d in result] == ["belege_jahresabschluss", "creditor"]
    assert result[0].attributes == []


def test_get_doc_type_parses_real_attributes_shape_format_isunique():
    """Regressionstest: reale Attribute stecken unter `attributes` mit
    `format`/`isunique`, NICHT `fields` mit `type`/`unique` wie ältere
    Spezifikationen annahmen (api-quirks.md Punkt 9) — falsch geparst gibt
    es dabei still eine leere Liste zurück statt eines sichtbaren Fehlers."""
    payload = {
        "id": 7580,
        "name": "creditor",
        "attributes": [
            {
                "name": "invoice_number",
                "default_value": None,
                "format": "string",
                "order": 1,
                "isunique": False,
                "required": False,
                "hidden": False,
                "isreference": 0,
            },
            {
                "name": "account_allocation",
                "default_value": None,
                "format": "json",
                "order": 16,
                "isunique": False,
                "required": True,
                "hidden": True,
                "isreference": 0,
            },
        ],
        "tags": ["cv-expenses-creditor"],
    }
    client = _client_with_transport(lambda request: httpx.Response(200, json=payload))
    result = client.get_doc_type("creditor")

    assert len(result.attributes) == 2
    assert result.attributes[0].format == "string"
    assert result.attributes[1].required is True
    assert result.attributes[1].hidden is True


def test_build_document_link_does_not_use_bearer_protected_attachment_url():
    """Regressionstest: der Browser-Link muss die öffentliche
    Weboberflächen-URL sein, nicht die Bearer-Token-geschützte Attachment-
    API-URL (api-quirks.md Punkt 11)."""
    link = build_document_link("https://web.kydo.example", org_id=79518, document_id=311983)
    assert link == "https://web.kydo.example/search/311983?org_id=79518"


def test_build_document_link_empty_when_no_document_id():
    assert build_document_link("https://web.kydo.example", org_id=1, document_id=None) == ""
