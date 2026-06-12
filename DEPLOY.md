# MedService — Production Deployment Runbook

Four components deploy together:

| Component | What | Served at |
|---|---|---|
| **backend** + **postgres** | FastAPI API + DB (+ `verify` scheduler sidecar) | `API_DOMAIN` |
| **frontend** | Next.js clinic dashboard | `APP_DOMAIN` |
| **mini** | Vite patient SPA (review links land here) | `MINI_DOMAIN` |
| **parsers** | review scrapers, baked into the backend image | — |

Topology: the backend + postgres run on one host (server 2); the frontend, mini,
and the edge **Caddy** (TLS + routing for all three domains) run on the other
(server 1). Caddy reverse-proxies `APP_DOMAIN`→frontend, `MINI_DOMAIN`→mini,
`API_DOMAIN`→backend private host. The mini calls a same-origin `/api` that its
own internal Caddy proxies to the backend, so no patient-facing CORS is needed.

> The code blockers from the readiness review are **already fixed** (admin
> bootstrap, branch assignment, mini deploy artifacts, env fail-fast guards,
> secret guard, verify scheduler, demo-content gate). This runbook is the
> operator checklist: env values, DNS, secrets, and post-deploy wiring.

---

## Phase 0 — Prerequisites

0. **Commit & push all four repos first.** Both `deploy.sh` scripts deploy via
   `git pull --ff-only`, so anything uncommitted locally (migrations, the mini's
   Dockerfile, `scripts/create_admin.py`, parser fixes, …) simply won't reach
   the server. Push `medservice-backend`, `medservice-frontend`,
   `medservice-mini`, and `medservice_parsers`, and make sure the server
   checkouts track the same branches.
1. Two hosts (or one) on a shared private network so Caddy can reach the backend
   at `BACKEND_PRIVATE_HOST:BACKEND_PRIVATE_PORT`. Docker + Docker Compose v2 on both.
2. DNS A-records → the Caddy host for **three** domains: `APP_DOMAIN`,
   `API_DOMAIN`, `MINI_DOMAIN`. Open ports **80/443** (ACME needs them).
   `ACME_EMAIL` must be a real address.
3. **Rotate the sms.ru API id** if it was ever committed to a tracked `.env`, and
   make sure no real `.env` is in git (`git ls-files | grep -i env` should show
   only `*.example`).

## Phase 1 — Fill env files (never commit them)

**Backend** — `medservice-backend/.env` (from `.env.production.example`):

- `ENVIRONMENT=production`, `DEBUG=False`
- `SECRET_KEY=$(openssl rand -hex 32)` — **not** a `REPLACE_*` placeholder. The
  app refuses to boot in production with a placeholder/short key, and `deploy.sh`
  refuses too.
- `POSTGRES_USER` / `POSTGRES_PASSWORD` (`openssl rand -base64 24`) / `POSTGRES_DB`
- `DATABASE_URL=postgresql://<user>:<password>@postgres:5432/<db>` (host = the
  compose service name `postgres`, password matching the above)
- `GUNICORN_WORKERS=1` (keep at 1 until parsing state is moved off the in-process
  global — see Known limitations)
- `BACKEND_BIND_IP=<this host's private IP>` — the interface port 8000 is
  published on (must exist on the machine, or compose fails to bind)
- `CORS_ORIGINS=https://<APP_DOMAIN>` (the mini is same-origin, so only the
  dashboard origin is required)
- `MINI_PUBLIC_URL=https://<MINI_DOMAIN>` (base of every review SMS link)
- `SMS_TEST_MODE=False`, `SMS_RU_API_ID=<real id>`, `SMS_SENDER=<approved sender>`
- `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` (for the first-admin bootstrap)
- `ALLOW_DEMO_BONUSES` — leave unset/False so patients never see fabricated offers
- `VERIFY_INTERVAL_SECONDS=1800` (review re-scrape cadence)

**Frontend** — `medservice-frontend/.env` (from `.env.example`):

- `NEXT_PUBLIC_API_URL=https://<API_DOMAIN>` (HTTPS, **never** localhost — the
  build fails otherwise)
- `APP_DOMAIN`, `API_DOMAIN`, `MINI_DOMAIN`, `ACME_EMAIL`
- `BACKEND_PRIVATE_HOST`, `BACKEND_PRIVATE_PORT` (where Caddy/mini reach the backend)

The mini needs no env file: it builds with an empty `VITE_API_URL` (same-origin
`/api`) and gets `BACKEND_PRIVATE_HOST/PORT` from the frontend compose.

## Phase 2 — Build, migrate, bring up

**Backend host:**
```
cd medservice-backend
./deploy.sh        # guards .env, pulls code+parsers, builds, migrates, starts
```
`entrypoint.sh` runs `alembic upgrade head` (chain `0001 → 0010_add_user_branches`)
then gunicorn. The `verify` sidecar starts the review-scrape loop. Confirm health:
`curl -fsS http://<backend>:8000/health`.

**Frontend host:**
```
cd medservice-frontend
./deploy.sh        # guards .env, builds frontend+mini, starts Caddy
```
After the frontend image builds, sanity-check the baked API URL:
`docker run --rm medservice-frontend:* sh -c 'grep -rl localhost .next/ ; true'`
(should find nothing) — or grep the served JS for `localhost:8000`.

## Phase 3 — Bootstrap & wiring

4. **Create the first admin** (NOT `seed.py`, which refuses in production):
   ```
   docker exec -it medservice_backend python scripts/create_admin.py
   ```
   (reads `ADMIN_USERNAME/EMAIL/PASSWORD` from the env). Log in at
   `https://<APP_DOMAIN>/admin/login`.
5. **Create clinic branches** in the admin panel (Филиалы) and fill each branch's
   **platform URLs** (Yandex/2GIS/etc.) — the verify scheduler needs them.
6. **Create clinic-manager accounts** in «Доступы» and **assign their branches**
   via the new checkboxes (a non-superuser with no branches sees an empty
   dashboard). Superusers see everything.

## Phase 4 — SMS go-live & smoke test

7. Confirm `SMS_TEST_MODE=False`, a valid `SMS_RU_API_ID`, an approved
   `SMS_SENDER`, and a real `MINI_PUBLIC_URL`. **Never run
   `scripts/start-sms-tunnel.sh` in production** — it overwrites `MINI_PUBLIC_URL`.
8. Send one live test SMS from a branch's mailing settings; confirm sms.ru reports
   *delivered* and the link opens `https://<MINI_DOMAIN>/r/<branchId>/<token>` —
   hard-refresh it to confirm the SPA fallback works (no 404).
9. End-to-end: rate → low score routes to «директору» and lands in «Перехваченные
   жалобы»; high score → platforms → "Я оставил отзыв" → the `verify` sidecar
   flips it to verified within `VERIFY_INTERVAL_SECONDS` once the review is scraped.
10. Dashboard: log in, exercise analytics, and verify admin impersonation
    enter/exit + the «Аккаунт Администратора» banner; confirm logout clears the
    session.

## Known limitations (track post-launch)

- **`GUNICORN_WORKERS=1` is required** until parsing status/locking moves out of
  the in-process module global (it is per-worker today, so >1 worker makes the
  "parsing already running" guard and `/parsing/status` unreliable).
- The `verify` sidecar logs to stdout (`docker logs medservice_verify`). Add
  alerting on repeated scrape failures so an anti-bot/captcha outage is caught
  before `mark_stale_not_found` flags real claims as `not_found` at 14 days.
- Migration `0010_add_user_branches` has **no backfill**: on an *upgrade-in-place*
  of a DB that already has non-superusers, assign their branches in the admin
  panel afterwards (a fresh deploy is unaffected).
- `Branch.avg_rating`/`nps_score` are dead cached columns (analytics computes
  live); don't rely on them.
