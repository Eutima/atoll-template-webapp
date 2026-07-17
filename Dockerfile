# syntax=docker/dockerfile:1

# ---- Stage: compile Tailwind CSS ----
FROM node:20-slim AS css-builder
WORKDIR /build
COPY package.json ./
RUN npm install
COPY tailwind.config.js postcss.config.js ./
COPY static/css/src ./static/css/src
COPY apps ./apps
COPY templates ./templates
RUN npm run build:css

# ---- Stage: install production Python dependencies ----
FROM python:3.12-slim AS py-builder
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/
RUN pip install --user --no-cache-dir -r requirements/production.txt

# ---- Stage: local development image (docker-compose.yml target) ----
FROM python:3.12-slim AS dev
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.development
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements/ requirements/
RUN pip install --no-cache-dir -r requirements/development.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ---- Stage: final production runtime ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/home/appuser/.local/bin:${PATH}"
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser
WORKDIR /app
COPY --from=py-builder /root/.local /home/appuser/.local
COPY --from=css-builder /build/static/css/dist ./static/css/dist
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

# Placeholder env vars satisfy production.py's required settings at build
# time only, so `collectstatic` (which never touches the database) can run
# without real infrastructure; real deployments override all of these.
RUN DJANGO_SECRET_KEY=build-time-placeholder \
    ALLOWED_HOSTS=localhost \
    POSTGRES_DB=build POSTGRES_USER=build POSTGRES_PASSWORD=build POSTGRES_HOST=localhost \
    python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
