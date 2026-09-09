# Testing

Detail for the testing rule in `CLAUDE.md`. These rules override defaults; follow them exactly.
`apps/authentication/tests/` is the reference suite — copy its shape.

## Two kinds of tests

- **Integration (the default — most tests live here).** Anything that touches the ORM, the Django test
  client, settings, migrations, auth, or an `interfaces/` client. Subclass `django.test.TestCase`. Test
  business logic at the **service** layer: call the service, assert the DB result and that the right
  `apps/shared/exceptions.py` exception is raised. Test **views** only for HTTP concerns — status code,
  rendered/serialized shape, permissions, redirects — don't re-assert business rules through the view.
- **Unit.** Pure Python with no Django involved — everything in `lib/`, plus small standalone
  helpers. Subclass `django.test.SimpleTestCase` (no DB access, no fixtures). Keep these fast and
  dependency-free.

Everything in `lib/` is unit-tested; if code under test needs the ORM, the client, settings, or an
external call, it's integration. When a Service is thin orchestration over a well-tested `lib/`
function, test the logic as a unit and give the Service one integration test for the
fetch / call / persist path.

## Layout

- `apps/<domain>/tests/test_<name>.py`, one file per concern, mirroring the source file it covers
  (`services/user_profile.py` → `tests/test_services.py`, `models/user_profile.py` → `test_models.py`,
  plus `test_managers`, `test_filters`, `test_permissions`, `test_serializers`, `test_views` as in
  `apps/authentication/tests/`).
- `interfaces/<system>/` gets its own `tests/` next to the client (see
  `apps/shared/interfaces/helix/tests/`).

## What to cover

- Every service method and view: the success path, **each** domain-exception branch, and
  permission / validation failures.
- Every bug fix lands with a regression test that fails without the fix.
- Query methods (QuerySet / Manager) get a test that pins their filtering / annotation.
- `create_user` / `create_superuser` on the custom user manager stay covered whenever that model moves.

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
