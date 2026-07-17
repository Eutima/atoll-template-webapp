---
name: kydo-api
description: Kydo-API-Integration (Dokumenten-Management, Buchungen/Journal, Kontenplan) — Auth-Muster, der 3-stufige Beleg-/Dokumenten-Upload, Paginierung und elf dokumentierte Spec-vs-Realität-Abweichungen. Verwenden bei jeder Arbeit mit der Kydo-API, einem KydoClient, Beleg-/Dokumenten-Upload nach Kydo, oder Kydo-Buchungen/Journal-/Kontenplan-Sync — unabhängig vom Projekt/Framework.
---

# Kydo API Integration

Dieser Skill ist projekt-/framework-unabhängig: `assets/kydo_client.py` ist
ein generischer, auf `httpx` + `pydantic` basierender Client ohne
Django-Abhängigkeit — einfach in ein beliebiges Python-Projekt kopieren
(z. B. als `repositories/kydo/client.py` oder ähnlich) und dort einen
projektspezifischen Aufrufer (Service, Task, o. ä.) darüberlegen.

## Grundmuster: Auth & jeder Request

Jeder Kydo-API-Call braucht zwei Dinge, ausnahmslos:

- Header `Authorization: Bearer <token>`
- Query-Parameter `org_id`

Beides gehört zentral in den `_request()`-Wrapper des Clients, nie an
einzelne Call-Sites — sonst vergisst man `org_id` garantiert irgendwo
(siehe `references/api-quirks.md`, Punkt 1). `KydoClient` in
`assets/kydo_client.py` macht das bereits so; beim Portieren in ein
Projekt diese Zentralisierung beibehalten.

Retries: 5xx-Antworten (500/502/503/504) und Verbindungsfehler werden mit
Backoff automatisch wiederholt (Default 3 Versuche), 4xx-Fehler nicht.
Alle Fehler nach ausgeschöpften Retries werden als `KydoApiError`
geworfen — Aufrufer müssen nur diesen einen Fehlertyp behandeln.

## Beleg-/Dokumenten-Upload: der 3-Schritt-Ablauf

Das ist bei Kydo immer dreistufig, unabhängig vom Projekt:

1. `upload_file(file_obj, file_name, doctype_name)` → `POST /v1/upload/file/`
   (multipart) → liefert eine `attachment_uuid`.
2. `create_document(doc_type_name, attributes)` →
   `POST /v1/docType/document/{doc_type_name}/` (JSON) → liefert die
   `document_id` **direkt in der Response** (entgegen mancher älterer
   OpenAPI-Doku, die "kein Response-Body" behauptet).
3. `link_attachment_to_document(document_id, attachment_uuid)` →
   `POST /v1/docType/document/{document_id}/attachment/` (JSON, **ohne**
   `/upload`-Suffix — das Suffix gehört zu einem anderen, hier nicht
   relevanten Endpunkt für neue Dateiversionen an einem *bestehenden*
   Dokument).

`attributes` in Schritt 2 baust du aus einem konfigurierbaren Feldmapping
(interner Feldname → Kydo-Attributname), nicht hartkodiert — jede Kydo-
Organisation kann eigene Doctype-Attribute haben. Rufe vorher
`get_doc_type(...)` ab, um die real existierenden Attributnamen zu prüfen
(siehe api-quirks.md Punkt 9 — das Antwortschema weicht von der Doku ab).

Für den Fall, dass kein Zwischenzustand zwischen den drei Schritten
benötigt wird, gibt es `KydoClient.upload_document(...)` als
Convenience-Wrapper um alle drei Aufrufe.

## Weitere Endpunkte (Kurzüberblick — Details in api-quirks.md)

- **Buchungen/Journal**: `list_bookings(...)` paginiert über
  `GET /v1/cv/journal/` (nicht `/v1/cv/bookings/`, das liefert 404 —
  Punkt 2). `tax` auf Buchungszeilen kommt als `""`, `{}` oder `null` und
  wird beim Parsen auf `None` normalisiert (Punkt 4).
- **Kontenplan**: `get_accounting_plan()` liest
  `GET /v1/finac/accounting_plan/`, nicht paginiert, Konten unter
  `accounts` verschachtelt (Punkt 5). Gruppen-/Kopfzeilen und oft auch
  `account_type` generell können `null` sein (Punkte 6/7) — für eine
  Kontotyp-Klassifizierung auf die Kontonummer zurückfallen, nicht auf
  `account_type` verlassen.
- **Doctypes**: `list_doc_types()` liefert Namen ohne Attribute;
  `get_doc_type(id_or_name)` liefert einen einzelnen Doctype **mit**
  Attributen unter dem Schlüssel `attributes` (`format`/`isunique`, nicht
  `fields`/`type`/`unique` — Punkt 9, ein besonders tückischer Fehler, da
  er still eine leere Liste statt eines Fehlers erzeugt).
- **Dokumenten-Links für Menschen**: `get_document_attachments()` liefert
  Bearer-Token-geschützte API-URLs, keine Browser-Links. Für einen
  klickbaren Link `build_document_link(web_base_url, org_id, document_id)`
  verwenden (Punkt 11) — braucht keinen zusätzlichen API-Call.

## Vorgehen beim Einbinden in ein neues Projekt

1. `assets/kydo_client.py` in das Zielprojekt kopieren.
2. Falls das Projekt eigene Verbindungsdaten verwaltet (z. B. ein Model
   mit `org_id`/Token pro Mandant), einen kleinen projekteigenen
   Konstruktor-Helper darüberlegen statt `KydoClient.from_env()` zu
   erzwingen — `from_env()` ist nur eine Bequemlichkeit für
   Skripte/Standalone-Nutzung.
3. `assets/test_kydo_client_example.py` als Ausgangspunkt für die eigenen
   Tests kopieren und den Import auf den tatsächlichen Pfad anpassen.
4. Bei neuen Endpunkten: erst gegen echte Zugangsdaten/Antworten
   verifizieren, dann implementieren — die offizielle Doku/Spezifikation
   war bei praktisch jedem bisher integrierten Endpunkt an mindestens
   einer Stelle falsch (siehe api-quirks.md). Neue Abweichungen dort
   ergänzen, nicht nur im Code kommentieren.

## Referenzen

- `references/api-quirks.md` — alle bekannten Endpunkte, Antwortformen und
  die dokumentierten Spec-vs.-Realität-Abweichungen. Immer zuerst lesen.
- `assets/kydo_client.py` — generischer, kopierbarer HTTP-Client (httpx)
  inkl. Pydantic-Modellen, Retry-Logik und Fehlerbehandlung.
- `assets/test_kydo_client_example.py` — Test-Mocking-Vorlage
  (`httpx.MockTransport`).
