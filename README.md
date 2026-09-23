# Django Template

[![Tests](https://github.com/roymanigley/blueprint-django-template/actions/workflows/tests.yml/badge.svg)](https://github.com/roymanigley/blueprint-django-template/actions/workflows/tests.yml)

A Django project template with a strict domain-driven architecture, [django-cotton](https://django-cotton.com) + [htmx](https://htmx.org) (+ [Alpine.js](https://alpinejs.dev)) for the frontend, and [l4py](https://pypi.org/project/l4py/) for structured logging. There is no database and no background worker — the only optional feature is session-only "Login with Helix" SSO.

## Architecture

```
config/                  Django project configuration
    settings/
        base.py           shared settings
        development.py    DEBUG=True, Debug Toolbar
        production.py     DEBUG=False, whitenoise, gunicorn
        test.py           test-only overrides

apps/
    shared/               base mixins, serializers, filters, views,
                          exceptions, middleware, external interfaces
        interfaces/       code talking to external systems (e.g. helix/)

    authentication/       optional "Login with Helix" session gate — the
                          reference implementation of the domain pattern:
        services/helix_login.py      OAuth2/PKCE flow (HelixLoginService)
        lib/helix_claims.py          pure claim-shaping helpers
        views/helix.py               HTTP concerns only
        permissions/helix.py         helix_login_required / mixin
        context_processors.py        exposes helix_user/helix_configured
        tests/                       one test file per concern
```

Every domain owns one file per concern (model, service, view, serializer,
filter, permissions, tests) — never one file per CRUD operation.

## Local development (no Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt

npm install
npm run build:css

cp .env.example .env   # edit as needed

python manage.py runserver
```

Visit:
- `/` — home page (open to everyone; shows "Log in with Helix" if configured)
- `/auth/login/` — log in with Helix (only available when `HELIX_*` env vars are set)

## Tests

Test config lives in `pytest.ini`, which pins `DJANGO_SETTINGS_MODULE` to
`config.settings.test`:

```bash
pytest
```

## Docker

### Development

```bash
docker compose up --build
```

Runs `web` (runserver, dev settings). No database, worker, or other external
services are required.

### Production-like

```bash
docker compose -f docker-compose.prod.yml up --build
```

Runs `web` (gunicorn). The production Docker image is built in stages
(Tailwind CSS via Node, Python dependencies, final slim runtime) so the
shipped image has no Node toolchain or dev dependencies.

## Environment variables

See `.env.example`. Never commit a real `.env` file.
