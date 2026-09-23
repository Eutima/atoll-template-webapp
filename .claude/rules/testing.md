# Testing

Detail for the testing rule in `CLAUDE.md`. These rules override defaults; follow them exactly.
`apps/authentication/tests/` is the reference suite — copy its shape.

## Two kinds of tests

- **Integration.** Anything that touches the Django test client, settings, sessions, or an
  `interfaces/` client. Test business logic at the **service** layer: call the service, assert the
  session/response result and that the right `apps/shared/exceptions.py` exception is raised. Test
  **views** only for HTTP concerns — status code, rendered/serialized shape, permissions, redirects —
  don't re-assert business rules through the view.
- **Unit.** Pure Python with no Django involved — everything in `lib/`, plus small standalone
  helpers.

This app has no database (`DATABASES = {}` in every settings file), so **every test in the repo
subclasses `django.test.SimpleTestCase`**, integration and unit alike — `SimpleTestCase` still gives
you the Django test client, `reverse()`, sessions, and `override_settings`, it just can't open a DB
transaction, which nothing here needs. `django.test.TestCase` is reserved for a future domain app that
reintroduces a database and real models; don't reach for it until one exists.

Everything in `lib/` is unit-tested; if code under test needs the test client, settings, sessions, or
an external call, it's integration. When a Service is thin orchestration over a well-tested `lib/`
function, test the logic as a unit and give the Service one integration test for the
fetch / call / persist path.

## Layout

- `apps/<domain>/tests/test_<name>.py`, one file per concern, mirroring the source file it covers
  (`services/helix_login.py` → `tests/test_helix_login_service.py`, `lib/helix_claims.py` →
  `test_lib_helix_claims.py`, plus `test_permissions`, `test_helix_views` as in
  `apps/authentication/tests/`).
- `interfaces/<system>/` gets its own `tests/` next to the client (see
  `apps/shared/interfaces/helix/tests/`).

## What to cover

- Every service method and view: the success path, **each** domain-exception branch, and
  permission / validation failures.
- Every bug fix lands with a regression test that fails without the fix.
- Query methods (QuerySet / Manager) get a test that pins their filtering / annotation, for any future
  domain app that reintroduces models.

## Style

- Method names read as `test_<behavior>_when_<condition>`.
- Arrange / act / assert, one behavior per test. No branching or loops in a test body.
- Build data with explicit helper functions, not shared fixtures or `setUp` mega-objects.
- Mock only true external boundaries — the `interfaces/<system>/` client, the clock, outbound HTTP.
  Never mock the ORM or code we own.

## Running

```bash
pytest
```
