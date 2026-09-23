# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Local setup (no Docker):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/development.txt
npm install && npm run build:css
cp .env.example .env
python manage.py runserver
```

This app has no database and no background worker — see "Settings split" and
"Login with Helix" below.

Tests run through `pytest` (config in `pytest.ini`, which pins `DJANGO_SETTINGS_MODULE` to `config.settings.test`):

```bash
pytest
pytest apps/authentication/tests/test_helix_login_service.py::HelixLoginServiceTests
```

Tailwind CSS (source `static/css/src/main.css` → compiled `static/css/dist/main.css`, which is gitignored):

```bash
npm run watch:css   # during development
npm run build:css   # one-off / before Docker build
```

Docker:

```bash
docker compose up --build                              # dev: web only, no external services
docker compose -f docker-compose.prod.yml up --build    # prod-like: web only
```

## Communicating with the user

The user is a business specialist, not a developer. In all responses (not just final summaries):

- Keep answers short and simple — as brief as possible while still answering the question.
- Avoid technical jargon, code snippets, file paths, and implementation detail unless explicitly asked for them.
- Frame explanations around business value and outcomes (what changed for them, what it enables, what to expect), not how it was built.

## Working conventions

- **Code style lives in `.claude/rules/code-style.md`.** Naming, imports, `X | None` type hints, double quotes, the view/service/serializer split, and domain-exception error handling. Read it before writing Python here.
- **Always enter plan mode for any prompt that isn't a question.** If the user's message is asking you to do something (implement, fix, refactor, add, remove, configure, etc.) rather than purely asking you to explain or answer something, enter plan mode before making any changes — even if the task seems small or the approach seems obvious. Only skip plan mode for genuine questions where no repo changes are being requested.
- **Don't build or run Docker unprompted.** `docker compose build`/`up` (dev or prod) is slow and noisy — only do it when the user explicitly asks to build, run, or test something in Docker. Local venv + `manage.py` is the default way to run and verify changes.
- **Every environment variable read by the code must be documented in `.env.example`.** Whenever you add or change an `os.environ[...]`/`os.environ.get(...)` call (or any other env var read, e.g. in `docker-compose*.yml`), add or update the matching key in `.env.example` with a safe placeholder/default value in the same change. Use the `env-example-sync` skill to check this.
- **Kydo integration work always goes through the `kydo-api` skill.** Any Kydo client code, tests, or notes on Kydo API behavior belong under `.claude/skills/kydo-api/` (`SKILL.md`, `references/api-quirks.md`, `assets/kydo_client.py`, `assets/test_kydo_client_example.py`) — don't scatter Kydo-related files elsewhere in the repo. Read `references/api-quirks.md` before implementing or changing any Kydo endpoint call, and add newly discovered spec-vs-reality deviations there rather than only as inline code comments.
- **"Login with Helix" work goes through the `helix-auth` skill.** Read `.claude/skills/helix-auth/SKILL.md` before touching the OAuth/PKCE flow, the `HELIX_*` settings, or `apps/shared/interfaces/helix/`. This app has no database, so login is gate-only and session-only: a successful callback (`apps/authentication/services/helix_login.py:HelixLoginService.complete_login`) stores a few identity claims (`sub`/`email`/`first_name`/`last_name`, via `apps/authentication/lib/helix_claims.py:build_session_claims`) directly in `request.session` — no user record is ever created or persisted. `apps/authentication/permissions/helix.py` (`is_helix_authenticated`, `helix_login_required`, `HelixLoginRequiredMixin`) is how an individual view opts into requiring a Helix session; nothing requires it by default. Helix `access_token`/`refresh_token` are used only inside the callback and never persisted.
- **Every change ships with tests.** New code gets tests that validate it; a bug fix gets a regression test that fails without the fix. Keep the suite green — it's the long-term stability guarantee. Conventions live in `.claude/rules/testing.md` (integration by default; unit only for `lib/` and other non-Django code).
- **Use the framework's tooling; don't hand-roll what a command generates.** Migrations come from `makemigrations` — hand-edit the generated file only for data migrations or operations the autodetector can't express, never write one from scratch. New apps come from `django-admin startapp`. Before calling a change done, run and clear `manage.py check` (dev + test) and `makemigrations --check --dry-run`.
- **Never wipe or delete data without the user's explicit consent.** This app has no database — the only persisted state is a browser's own session — but the principle still applies to whatever local/runtime state a future change introduces. Treat existing data as something to preserve; if a data problem needs resolving, fix it forward instead of resetting it.
- **Restart the app when you're done.** After finishing a change, run/restart `python manage.py runserver` so the app is left running the latest code.

## Architecture

### Domain-driven layout, not Django's default per-app layout

Everything lives under `config/` (project config) and `apps/` (domains). Within a domain app, each concern gets **exactly one file**, never one file per model/CRUD operation:

```
apps/<domain>/
    models/<name>.py       QuerySet + Manager + Model, all three in the same file
    lib/<name>.py          auxiliary framework-free classes/functions: no ORM, no Django/interfaces imports, no I/O; unit-tested
    services/<name>.py     one Service class: business logic, calls Managers/QuerySets/interfaces/lib
    views/<name>.py        HTTP concerns only (auth, response shaping); calls the Service, never touches the ORM directly
    serializers/<name>.py  request validation / response shaping
    filters/<name>.py      django_filters.FilterSet
    permissions/<name>.py  authorization helpers/mixins
    tests/test_<name>.py
```

`apps/authentication/*/helix.py` (and `services/helix_login.py`) is the reference implementation of this pattern — copy its shape when adding a new domain.

`apps/shared` is the base layer: `apps/authentication` may depend on it, but it must never import from a domain app. External system integrations (Helix OAuth today) live under `apps/shared/interfaces/<system>/` — that's the only code allowed to call the external API/SDK directly.

### No DRF

Despite "serializers" and "filters" in the naming, this project does **not** use Django REST Framework. `apps/shared/serializers.py:BaseSerializer` is a small hand-rolled class (`fields()`, `validate_<field>()` hooks, `is_valid()`, `.errors`, `.data`) used for plain-view request validation and response shaping. `django-filter`'s `FilterSet` is used standalone (not DRF's `DjangoFilterBackend`) via `apps/shared/filters.py:SearchFilterMixin` + `BaseFilterSet`. Backend-searched, paginated list endpoints are built on `apps/shared/views.py:SearchEndpointView`, which any domain subclasses by setting `filterset_class`, `result_template_name`, and overriding `get_queryset()` to go through its Service.

### No database, no background worker

`DATABASES = {}` in every settings file — this template ships with no ORM-backed app and no relational database. Sessions use `SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"` (session data lives signed in the cookie itself, never server-side), so only small, non-secret Helix identity claims ever go in `request.session` — never tokens. A future domain app that needs real persistence would reintroduce `DATABASES`, `AUTH_USER_MODEL`, and DB-backed sessions deliberately; until then, don't add models, migrations, or a Huey-style worker without discussing the tradeoff with the user first.

### Settings split

`config/settings/{base,development,production,test}.py`. Django Debug Toolbar is added to `INSTALLED_APPS`/`MIDDLEWARE` **only inside `development.py`**, never conditionally in `base.py` — this is deliberate so it structurally cannot leak into production regardless of `DEBUG`'s value there (`production.py` also has a defensive `assert "debug_toolbar" not in INSTALLED_APPS`).

Logging goes through `l4py` (`LogConfigBuilderDjango` in each settings file). `l4py` defaults to **also** writing a log file to the current working directory even when no `.file(...)` path is configured — `.file_enabled(False)` is set explicitly in `base.py`/`development.py` to keep logging console-only (containers log to stdout). Don't remove that call without deliberately wanting log files on disk. `apps/shared/middleware.py:LoggingContextMiddleware` sets `l4py`'s trace_id/user_id context vars per request, so every log line during a request carries them automatically.

### Frontend: django-cotton + htmx + Alpine.js, no build-time JS framework

Cotton components live in `<app>/templates/cotton/*.html` and are invoked as `<c-component-name attr="...">`, with `<c-vars .../>` declaring props (see `apps/shared/templates/cotton/layout.html` and `searchable_select.html`). htmx and Alpine.js are vendored static files under `static/js/vendor/` (not CDN-loaded), for reproducible offline Docker builds. The searchable-dropdown pattern (`<c-searchable-select>` + `apps/shared/views.py:SearchEndpointView` + a domain's `*_options.html` result partial) is the template for any future backend-searched dropdown — never load full tables client-side for this.

`STATICFILES_DIRS`/cotton's `templates/` auto-discovery mean both project-level (`templates/`, `static/`) and per-app (`apps/*/templates/`, `apps/*/static/`) directories are valid places to add files; app-level is preferred for anything domain-specific.
