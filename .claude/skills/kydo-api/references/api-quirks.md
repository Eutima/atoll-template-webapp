# Kydo API: Endpunkte & dokumentierte Spec-vs-Realität-Abweichungen

Alle Punkte hier wurden gegen echte Kydo-Zugangsdaten/-Antworten verifiziert.
Wo die Spezifikation/OpenAPI-Doku etwas anderes behauptet, steht das
ausdrücklich dabei — im Zweifel gewinnt dieses Dokument gegen die Doku.

## 1. `org_id` ist auf JEDEM Request Pflicht

Jeder Call gegen die Kydo-API braucht den Query-Parameter `org_id`,
zusätzlich zum `Authorization: Bearer <token>`-Header. Das ist eine harte
Anforderung — nicht optional pro Endpunkt. Deshalb im generischen Client
zentral im `_request()`-Wrapper setzen, nie an einzelnen Call-Sites, sonst
vergisst man es garantiert irgendwo.

## 2. Buchungen: `/v1/cv/bookings/` existiert nicht — `/v1/cv/journal/` verwenden

Die Spezifikation ging (laut Auftraggeber seinerzeit bestätigt) von
`/v1/cv/bookings/` aus. Gegen die reale API liefert das einen 404. Der
tatsächlich funktionierende Pfad ist `/v1/cv/journal/` — liefert dieselben
Daten (u. a. dasselbe `document`-Feld, das im CSV-Export als
`/search/<document>`-Link auftaucht).

## 3. Buchungsliste: cursor-artige Paginierung über `results` + `next`

`GET /v1/cv/journal/` liefert `{"results": [...], "next": <url-oder-null>}`.
`next: null` (oder Schlüssel fehlt) heisst „letzte Seite". Leere `results`
ist ebenfalls ein Abbruchkriterium (Sicherheitsnetz gegen Endlosschleifen
bei unerwarteten Antwortformen).

## 4. `tax` auf Buchungszeilen: `""`, `{}` und `null` bedeuten alle „kein Steuercode"

Für Bookings ohne MWST liefert die reale API `tax` je nach Fall als leeren
String, leeres Dict oder `null` — alle drei müssen als „kein Steuercode"
(also `None`) behandelt werden. Am saubersten mit einem Pydantic
`field_validator(mode="before")` direkt beim Parsen normalisieren, nicht an
jeder Verwendungsstelle einzeln prüfen.

## 5. Kontenplan: nicht paginiert, Konten unter `"accounts"` verschachtelt

`GET /v1/finac/accounting_plan/` gibt die Konten NICHT als Liste auf
oberster Ebene zurück, sondern verschachtelt unter dem Schlüssel
`accounts`. Keine Paginierung — eine Antwort enthält alles.

## 6. Kontenplan: Gruppen-/Kopfzeilen liefern mehrere Felder als `null`

Reine Gruppen-/Kopfzeilen (z. B. eine Kontengruppe selbst, kein eigenes
bebuchbares Konto) liefern `id`, `is_active`, `is_locked` und
`account_type` als `null`. Das Pydantic-Modell muss das tolerieren (Felder
optional UND `None`-fähig), und nachgelagerte Logik sollte solche Zeilen
einzeln überspringen statt die ganze Antwort abzulehnen.

## 7. `account_type` ist in der Praxis oft für ALLE Konten `null`

Nicht nur bei Gruppenzeilen (Punkt 6) — in der Praxis liefert Kydo für
komplette Kontenpläne häufig durchgängig `account_type=null`. Eine
Klassifizierung darf sich also nicht primär auf `account_type` verlassen,
sondern sollte auf die erste Ziffer der Kontonummer zurückfallen (z. B.
Schweizer KMU-Kontenrahmen-Konvention), mit Kontonummer als robusterem
Signal.

## 8. Doctype-Liste liefert KEINE Attribute — einzeln nachladen

`GET /v1/docType/doc_type/` liefert alle Dokumenttypen als flache Liste,
aber ohne deren Attribute. Attribute gibt es nur über
`GET /v1/docType/doc_type/{id_or_name}/` für einen einzelnen Doctype.

## 9. Doctype-Attribute: `attributes`/`format`/`isunique`, nicht `fields`/`type`/`unique`

Ältere Spezifikationen nahmen fälschlich einen Schlüssel `fields` mit den
Feldern `type`/`unique` an. Die reale Antwort verschachtelt die Attribute
unter `attributes`, mit den Feldern `format` (statt `type`) und `isunique`
(statt `unique`). **Gefährlich still**: Pydantic ignoriert unbekannte
Schlüssel per Default und füllt den Default-Wert (leere Liste) — ein
falsches Schema führt hier NICHT zu einem sichtbaren Fehler, sondern zu
einer scheinbar korrekten, aber leeren Attributliste. Immer gegen eine
echte Antwort verifizieren, nicht nur gegen die Doku programmieren.

## 10. Beleg-/Dokumenten-Upload: der 3-Schritt-Ablauf

Siehe SKILL.md für die ausführliche Beschreibung. Kurzfassung der drei
Abweichungen von der Doku:

- **10a** `POST /v1/upload/file/` (Schritt 1) liefert die Attachment-UUID
  im Feld `uuid`.
- **10b** `POST /v1/docType/document/{doc_type_name}/` (Schritt 2) liefert
  die `document_id` **direkt in der Response** (Feld `id`) — entgegen
  mancher älterer OpenAPI-Doku, die "kein Response-Body" behauptet.
- **10c** `POST /v1/docType/document/{document_id}/attachment/` (Schritt 3)
  hat **kein** `/upload`-Suffix. Das Suffix gehört zu einem anderen,
  hier nicht relevanten Endpunkt für neue Dateiversionen an einem
  *bestehenden* Dokument — leicht zu verwechseln, da beide Endpunkte unter
  `/docType/document/.../attachment/` liegen.

## 11. Attachment-URLs aus `get_document_attachments()` sind KEINE Browser-Links

Die von `GET /v1/docType/document/{id}/attachment/` gelieferte URL zeigt
auf die reine API (Bearer-Token-geschützt). Im Browser geöffnet liefert
das `{"detail":"Authentication credentials were not provided."}`. Für
einen klickbaren, öffentlich aufrufbaren Link stattdessen selbst bauen:

```
{KYDO_WEB_BASE_URL}/search/{document_id}?org_id={org_id}
```

Das entspricht dem realen `Reference`-URL-Muster aus dem Kydo-CSV-Export
und braucht keinen zusätzlichen API-Call, sobald man die `document_id`
bereits kennt (z. B. aus dem `document`-Feld einer Journal-Buchung).

## Basis-URLs

Zwei getrennte Basis-URLs, nicht verwechseln:

- API-Basis (z. B. `https://api.kydo.ch`) — für alle `KydoClient`-Aufrufe.
- Web-Basis (z. B. `https://web.kydo.ch` bzw. je nach Umgebung) — nur für
  den in Punkt 11 gebauten Browser-Link, nie für API-Requests.
