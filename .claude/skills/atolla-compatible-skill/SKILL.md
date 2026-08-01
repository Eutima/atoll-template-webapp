---
name: atolla-compatible
description: Adapts the current repository so it can be deployed on the Atolla deployment platform (Dockerfile, health-check endpoint, .env.example, DB/worker conventions). Use when the user asks to "make this atolla compatible", "prepare this repo for atolla deployment", "onboard this app to atolla", or similar.
---

# Make this repository Atolla-compatible

Atolla is a self-hosted deployment platform. It has **no manifest file** (no
`atolla.yaml`, no `Procfile`, no buildpacks) and **no callback API the app must
implement**. Its entire compatibility contract boils down to four things:

1. A root `Dockerfile` that builds and runs a production-ready image with a
   plain `docker build .` — no build args, no build-time secrets, no
   `--target` flag. Whatever the **last stage** of the Dockerfile is, that's
   what gets built and run.
2. A root `.env.example` (or `example.env`) file listing every environment
   variable the app needs, one `KEY=` per line. Atolla only reads the *key
   names* from this file — it uses them to know which variables an operator
   must supply a value for in its console. If a key is expected but has no
   value set, **the deployment is blocked** before the image is even built.
3. Exactly one HTTP health-check endpoint that returns HTTP `200`. The port
   and path are **fixed by which deployment profile an Atolla operator picks
   for this app** — the repo cannot declare a custom port or path itself.
   The three profiles in use today:

   | Profile          | Container port | Health-check path |
   |------------------|-----------------|--------------------|
   | Django-style      | `8000`          | `/metrics`         |
   | Static/Angular-style | `80`         | `/`                |
   | Generic           | `8000`          | `/`                |

4. If the app needs a database or a background worker, it should read their
   connection info from a fixed set of env var names (below) — Atolla
   provisions sibling `db`/`redis` containers and pre-seeds these values, it
   does not let the app name them itself.

Explicitly **out of scope** — do not add these, they are not part of the
contract and Atolla will not use them:
- Any `atolla.yaml`/`atolla.json`/manifest file.
- A GitHub Actions workflow or any other CI pipeline (Atolla deploys via its
  own webhook-triggered pipeline, not via CI).
- Any webhook, callback, or "report deployment status" endpoint the app must
  expose — Atolla never calls back into the deployed app except the single
  health-check GET.
- Reading `PORT` from the environment to decide what to bind to — the port
  is fixed by the profile, not passed in at runtime as a `PORT` var (unless
  the app already does this for other reasons; don't add it solely for Atolla).

## Procedure

Work through these steps in order. Make the changes directly in this repo.

### 1. Detect the stack

Identify the language/framework and existing entrypoint: look for
`package.json`, `requirements.txt`/`pyproject.toml`, `go.mod`, `Gemfile`,
`composer.json`, an existing `Dockerfile`, and the app's web framework
(Django, Express, Flask, Rails, Spring, etc.) and its router/URL config.

### 2. Ask which profile applies

Before writing the Dockerfile and health check, ask the user (they'll need to
confirm this with whoever administers their Atolla instance, since it's an
operator-side setting):

- Which profile will this app be deployed under: **Django-style** (port
  8000, health path `/metrics`), **static/Angular-style** (port 80, health
  path `/`), or **generic** (port 8000, health path `/`)? If none of the
  presets match the framework, pick the generic profile's port/path
  (`8000` / `/`) as the safe default and note that the operator may need to
  add a custom profile on their end if a different port is required.
- Does this app need a database? (assume PostgreSQL if yes — that's the only
  database Atolla provisions today)
- Does this app run a background worker process?
- Will this app need a custom domain?

Don't guess these — they change what you build in steps 3–6.

### 3. Root Dockerfile

- If a root `Dockerfile` already exists, check that its **final stage**
  produces a directly runnable production image (not a dev/test stage) and
  that `docker build .` would succeed with no required `--build-arg` or
  secrets. Fix it if it fails either check (e.g. reorder multi-stage builds
  so the production stage is last, remove reliance on build args for
  required config — config should come from env vars at runtime instead).
- If no Dockerfile exists, create a minimal production one appropriate to
  the detected stack: install dependencies, copy source, expose the port
  chosen in step 2, and run the production entrypoint (e.g. `gunicorn`,
  `node server.js`, a compiled binary, an nginx-served static build, etc.)
  — whatever is idiomatic for this stack.
- Make sure the app listens on `0.0.0.0` on the chosen container port, not
  `127.0.0.1`/`localhost`.

### 4. Health-check endpoint

Add (or verify) a route at the path chosen in step 2 that returns a plain
HTTP `200` with no required auth. Wire it into the app's actual router in a
way idiomatic to the framework (e.g. a Django URL pattern, an Express route,
a Rails route, a Spring `@GetMapping`). A trivial static `200 OK` body is
sufficient — Atolla only checks the status code.

### 5. `.env.example`

Scan the codebase for every place it reads configuration from the
environment (`os.environ`/`os.getenv` in Python, `process.env` in
Node/JS/TS, `System.getenv`/Spring `@Value` in Java, `ENV[...]` in Ruby,
`os.Getenv` in Go, etc.). Create or update a root `.env.example` (or
`example.env` if the repo already uses that name) listing every discovered
key as `KEY=` (no real values — placeholders or blank). Preserve any
existing entries already in the file; add missing ones; don't remove
entries you can't confirm are unused.

### 6. Testing (Python projects only)

If the detected stack is Python, make sure **pytest** is the test runner used
to validate your changes:
- If a test suite already exists under a different runner (`unittest`,
  `nose`, etc.), don't rewrite it — pytest can discover and run
  `unittest`-style tests natively. Just make sure `pytest` is installed
  (added to `requirements-dev.txt`/`pyproject.toml`'s dev/test dependency
  group, whichever the repo already uses) and that running `pytest` from the
  repo root actually discovers and runs the existing tests.
- If no test suite exists yet, add a minimal smoke test (e.g.
  `tests/test_health.py`) that exercises the health-check route added in
  step 4, using `pytest`.
- Run `pytest` and confirm it passes before considering the adaptation
  complete. This is a sanity check on the changes you just made (Dockerfile,
  health-check route), not something Atolla itself requires — Atolla's
  pipeline does not run the app's test suite.

### 7. Database and worker conventions (only if applicable)

- **If a database was requested in step 2**: make sure the app's DB config
  resolves connection info from `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
  `DB_PASSWORD` (default `DB_HOST=db`, `DB_PORT=5432` once deployed). If the
  app currently uses differently-named variables (e.g. `DATABASE_URL`,
  `POSTGRES_HOST`), either add support for these names alongside the
  existing ones, or clearly document the mapping in `.env.example` with a
  comment. Add all five keys to `.env.example`.
- **If a worker was requested in step 2**: make sure the worker/queue config
  resolves `REDIS_HOST` and `REDIS_PORT` (default `REDIS_HOST=redis`,
  `REDIS_PORT=6379`) and add them to `.env.example`. Do not hardcode a
  worker start command in the repo expecting Atolla to discover it — the
  worker's start command is configured on the Atolla side. Call this out in
  your final summary so the user tells their operator the exact command to
  run (e.g. `celery -A app worker`, `node worker.js`, `bin/worker`).
- **If a custom domain was requested in step 2**: no repo change is needed;
  note in your final summary that the operator will need to set a
  `HOST_PORT` variable on their end and configure the domain in the Atolla
  console.

### 8. Final summary

Report back concisely:
- What files you created/changed (Dockerfile, health-check route,
  `.env.example`, any config changes for DB/worker env var names, any test
  files added).
- For Python projects: confirmation that `pytest` runs and passes.
- The exact container port and health-check path the app now serves, and
  which profile that matches.
- A short checklist of what's left for the user to coordinate with their
  Atolla operator, e.g.:
  - Confirm/select the matching deployment profile for this repo.
  - Set real values for every key in `.env.example` in the Atolla console.
  - Map the deployment branch(es) to environment(s).
  - If a worker is used: tell the operator the worker start command.
  - If a custom domain is planned: request a `HOST_PORT` variable and
    domain configuration.
  - If deployment approval gates are desired: ask the operator to enable
    them and list approvers for the relevant environment.
