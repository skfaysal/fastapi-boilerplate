# Secrets Runbook

Short operational notes for handling the app's secrets. Keep this current.

## What is a secret here

| Secret | Where | Notes |
|---|---|---|
| `JWT_SECRET_KEY` | `.env` | Signs/verifies every JWT. Different value per environment. |
| `DATABASE_URL` | `.env` | Contains the DB password. |

## Rules

- **Never commit real secrets.** `.env` is gitignored (verify: `git check-ignore .env` prints `.env`). Only `.env.example` (placeholders) is committed.
- **One secret per environment.** dev / staging / prod each get their own `JWT_SECRET_KEY`. Never reuse prod's anywhere else.
- **In production, inject secrets from the platform** (Docker/K8s secret, cloud secret manager), not from a file on disk.

## Generate a strong key

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Rotating `JWT_SECRET_KEY`

Changing the key immediately **invalidates every existing token** (all users must log in again). That's the intended behavior after a suspected leak.

1. Generate a new key (command above).
2. Set it in the environment's secret store / `.env` and restart the app.
3. Expect a spike of `401`s as old access tokens fail; clients hit `/auth/refresh`, which also fails (refresh tokens are signed with the same key), so they fall back to `/auth/login`. This is a forced global re-login — communicate it if planned.
4. (Optional, zero-downtime) support two keys during a window: verify against `{old, new}`, sign only with `new`. Not implemented here — noted as the upgrade path.

## If a secret leaks

1. Rotate `JWT_SECRET_KEY` immediately (above) — this kills all sessions.
2. If `DATABASE_URL` leaked: rotate the DB password, update the secret, restart.
3. Review auth-failure logs (structured JSON, filter `message` for `auth failed`) around the incident window.
