# Django Template

A Django project template with a strict domain-driven architecture, [django-cotton](https://django-cotton.com) + [htmx](https://htmx.org) (+ [Alpine.js](https://alpinejs.dev)) for the frontend, [Huey](https://huey.readthedocs.io) for background jobs, and [l4py](https://pypi.org/project/l4py/) for structured logging.

## Architecture

```
config/                  Django project configuration
    settings/
        base.py           shared settings
        development.py    DEBUG=True, SQLite, SqliteHuey, Debug Toolbar
        production.py     DEBUG=False, Postgres, RedisHuey, whitenoise, gunicorn
        test.py           in-memory SQLite, SqliteHuey(immediate=True)

apps/
    shared/               base models, mixins, serializers, filters, views,
                          exceptions, middleware, external interfaces
        interfaces/       code talking to external systems (e.g. smtp/)

    authentication/       UserProfile domain (custom user model) — the
                          reference implementation of the domain pattern:
        models/user_profile.py       QuerySet + Manager + Model
        services/user_profile.py     business logic (UserProfileService)
        views/user_profile.py        HTTP concerns only
        serializers/user_profile.py  request validation / response shaping
        filters/user_profile.py      django-filter FilterSet
        permissions/user_profile.py  authorization helpers
        tests/                       one test file per concern

    jobs/                 Huey background jobs / scheduled tasks; jobs call
                          Services, never duplicate business logic
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

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

In a second terminal, run the Huey consumer to process background jobs:

```bash
python manage.py run_huey
```

Visit:
- `/admin/` — Django admin
- `/auth/login/`, `/auth/signup/` — authentication
- `/demo/searchable-select/` — searchable dropdown demo (backend search via
  htmx, keyboard navigation via Alpine.js)

## Tests

```bash
python manage.py test
```

Runs against `config.settings.test` is implied by `manage.py` picking up
`DJANGO_SETTINGS_MODULE`; to force it explicitly:

```bash
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py test
```

## Docker

### Development

```bash
docker compose up --build
```

Runs `web` (runserver, dev settings) and `huey` (Huey consumer) against
SQLite with no external services required.

### Production-like

```bash
docker compose -f docker-compose.prod.yml up --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Runs `web` (gunicorn) and `huey` against Postgres + Redis. The production
Docker image is built in stages (Tailwind CSS via Node, Python dependencies,
final slim runtime) so the shipped image has no Node toolchain or dev
dependencies.

## Environment variables

See `.env.example`. Never commit a real `.env` file.
