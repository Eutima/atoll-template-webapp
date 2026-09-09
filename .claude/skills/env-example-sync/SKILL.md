---
name: env-example-sync
description: Keeps .env.example in sync with the environment variables actually read by the code. Use whenever adding, renaming, or removing an os.environ / os.environ.get / os.getenv read in config/settings/*.py or apps/**, or an environment: entry in docker-compose*.yml — and before reporting any such change as done.
---

# env-example-sync

`.env.example` is the single source of truth for which environment
variables this project uses. It must always list **every** variable the
code actually reads — new variables missing from it silently break fresh
`cp .env.example .env` setups and Docker builds.

## When to run this

Any time you touch code that reads an environment variable:

- `os.environ["X"]` / `os.environ.get("X", ...)` / `os.getenv("X", ...)`
  anywhere under `config/settings/` or `apps/`.
- `environment:` blocks in `docker-compose.yml` / `docker-compose.prod.yml`
  that reference `${X}`.

Run it before reporting the change as complete, not just when explicitly
asked — this is a "did I forget something" check, not a standalone task.

## How to check

1. Collect every env var actually read by the code:

   ```bash
   grep -rhoE 'os\.environ(\.get)?\(\s*"[A-Z0-9_]+"|os\.environ\["[A-Z0-9_]+"\]|os\.getenv\(\s*"[A-Z0-9_]+"' \
     config/ apps/ | grep -oE '"[A-Z0-9_]+"' | tr -d '"' | sort -u
   ```

   Also check `docker-compose.yml` / `docker-compose.prod.yml` for
   `${VAR}` references in `environment:` blocks — those come from the
   same `.env` file (`env_file: .env`) and must be in `.env.example` too.

2. Collect every key currently declared in `.env.example`:

   ```bash
   grep -oE '^[A-Z0-9_]+=' .env.example | tr -d '='
   ```

3. Diff the two lists.
   - **Missing from `.env.example`**: add a line `KEY=<placeholder>` under
     the appropriate section comment (`# Django`, `# Database`, `# Redis /
     Huey`, `# l4py logging`, `# Helix OAuth / OIDC`, or a new section
     if it's a genuinely new integration). Use a safe non-secret
     placeholder value (e.g. `changeme`, a working local default, or
     empty string), never a real credential.
   - **Present in `.env.example` but no longer read anywhere in the
     code**: remove the line — stale entries are misleading.

4. If a variable is only relevant to one settings module (e.g.
   `DB_*`/`REDIS_*` are only read by `config/settings/production.py`),
   keep the existing convention of a comment noting that, e.g.
   `# (used only when DJANGO_SETTINGS_MODULE=config.settings.production)`
   — see the existing `.env.example` for the pattern.

## Notes

- `.env` itself is gitignored and machine-specific; never edit it on the
  user's behalf. `.env.example` is the checked-in, committed template.
- This is unrelated to Kydo API credentials/config — those follow the
  same `.env.example` rule but see the `kydo-api` skill for anything
  Kydo-specific.
