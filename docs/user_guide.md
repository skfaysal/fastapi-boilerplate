# User Guide — Test Every Feature, Step by Step

A hands-on playbook for a **learner**: after starting the server, run these commands
top-to-bottom to exercise every endpoint and every topic this repo covers, and see the
proof each feature works. Commands are copy-paste-runnable (they use `curl` + `jq`).

- **Why** each piece exists → [`boilerplate_guide.md`](./boilerplate_guide.md) (section refs like *§16* below point there).
- This guide is the **how do I try it** companion, and it's **evolving** — add a block when you add a feature.

> **Prereq for copy-paste:** [`jq`](https://jqlang.github.io/jq/) (`brew install jq`). Or drop the `jq` bits and copy tokens by hand. Alternatively, do it all in **Swagger UI** at `http://localhost:8000/docs` (click **Authorize**).

---

## 0. Start the server

```bash
uv sync                                   # install deps
cp .env.example .env                      # then edit: set DATABASE_URL + JWT_SECRET_KEY
uv run alembic upgrade head               # build schema (incl. is_admin column)
uv run uvicorn src.main:app --reload      # → http://localhost:8000
```

Set a base URL for every command below:
```bash
export BASE=http://localhost:8000/api/v1
```

> Keep the server terminal visible — several tests below are verified by watching its **logs**.

---

## Topics → where to test

| # | Topic (guide §) | Test section |
|---|---|---|
| Auth flow (§07–09) | register → login → protected → refresh → logout | [1](#1-the-core-auth-flow) |
| Pydantic validation (§04) | 422s, field/model validators | [2](#2-validation-04) |
| Books CRUD (§05) | create/read/update/delete | [3](#3-books-crud-05) |
| Pagination/filter/sort (§14) | `limit/offset/sort_by/order/author` | [4](#4-pagination-filtering--sorting-14) |
| Consistent errors (§11) | 404 / 422 / 401 shape | [5](#5-consistent-error-shape-11) |
| Middleware (§12) | request-id + timing headers | [6](#6-middleware-headers-12) |
| Lifespan (§13) | startup/shutdown logs | [7](#7-lifespan-13) |
| Rate limiting (§16) | 429 on brute-force | [8](#8-rate-limiting-16) |
| JSON logging (§17) | structured log lines | [9](#9-structured-json-logging-17) |
| Env-gated docs (§18) | `/docs` hidden in prod | [10](#10-environment-gated-docs-18) |
| RBAC admin (§19) | 403 vs admin 200 | [11](#11-rbac--admin-19) |
| Secrets (§20) | gitignore + rotation | [12](#12-secrets-20) |
| Tests (§15) | `pytest` | [13](#13-run-the-test-suite-15) |
| MongoDB activity log (§21) | `/activity` audit feed | [14](#14-mongodb-activity-log-21) |

---

## 1. The core auth flow

### 1a. Register a user (§07)
```bash
curl -s -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"Alice","email":"Alice@Example.com","first_name":"Al","last_name":"Ice","password":"supersecret123"}' | jq
```
**Expect:** `201`; body is the user with `"username":"alice"` and `"email":"alice@example.com"` (lowercased), **no** `hashed_password`, and `"is_admin": false`.

### 1b. Log in → capture tokens (§08)
```bash
ACCESS=$(curl -s -X POST $BASE/auth/login -d "username=alice@example.com&password=supersecret123" | jq -r .access_token)
REFRESH=$(curl -s -X POST $BASE/auth/login -d "username=alice@example.com&password=supersecret123" | jq -r .refresh_token)
echo "ACCESS=$ACCESS"
```
**Expect:** two long JWT strings. (Login uses the OAuth2 **form**, so `username` carries the email.)

### 1c. Call a protected endpoint (§09)
```bash
curl -s $BASE/auth/me -H "Authorization: Bearer $ACCESS" | jq
curl -s -o /dev/null -w "no-token: %{http_code}\n" $BASE/auth/me      # → 401
```
**Expect:** `/auth/me` returns your user; without the header → `401`.

### 1d. Refresh — rotation & reuse detection (§08)
```bash
# Swap the refresh token for a brand-new pair:
NEW=$(curl -s -X POST $BASE/auth/refresh -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH\"}")
echo $NEW | jq
# Now REPLAY the OLD refresh token — it was rotated, so it must be rejected:
curl -s -X POST $BASE/auth/refresh -H "Content-Type: application/json" -d "{\"refresh_token\":\"$REFRESH\"}" | jq
```
**Expect:** first call → new `access_token` + `refresh_token`; replay of the old one → `401` (`Invalid or expired refresh token`). Reusing a rotated token is treated as theft and revokes the whole token family.

### 1e. Logout (§08)
```bash
NEW_REFRESH=$(echo $NEW | jq -r .refresh_token)
curl -s -o /dev/null -w "logout: %{http_code}\n" -X POST $BASE/auth/logout \
  -H "Content-Type: application/json" -d "{\"refresh_token\":\"$NEW_REFRESH\"}"   # → 204
```
**Expect:** `204`. That refresh token can no longer mint access tokens.

> Re-run **1b** to get a fresh `ACCESS`/`REFRESH` for the sections below.

---

## 2. Validation (§04)

```bash
# Too-short password → 422
curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" \
  -d '{"username":"bob","email":"bob@example.com","first_name":"B","last_name":"O","password":"short"}' | jq

# model_validator: password contains the username → 422
curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" \
  -d '{"username":"charlie","email":"c@example.com","first_name":"C","last_name":"H","password":"charlie-secret"}' | jq

# Bad email format → 422
curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" \
  -d '{"username":"dan","email":"not-an-email","first_name":"D","last_name":"N","password":"supersecret123"}' | jq
```
**Expect:** every one → `422` with `"code":"validation_error"` and a `detail` array pointing at the offending field.

---

## 3. Books CRUD (§05)

All `/books` routes need a token. Create one and note its id:
```bash
BOOK=$(curl -s -X POST $BASE/books -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"title":"Clean   Code","author":"Robert Martin","year":2008,"price":30.5}')
echo $BOOK | jq
BID=$(echo $BOOK | jq -r .id)
```
**Expect:** `201`; note `"title":"Clean Code"` — the **field_validator** collapsed the triple space (§04).

```bash
curl -s $BASE/books/$BID -H "Authorization: Bearer $ACCESS" | jq          # read one
curl -s -X PUT $BASE/books/$BID -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" -d '{"price":25.0}' | jq            # partial update
curl -s -o /dev/null -w "delete: %{http_code}\n" -X DELETE $BASE/books/$BID -H "Authorization: Bearer $ACCESS"  # → 204
```
**Expect:** read → the book; update → `price` changed, other fields untouched (`exclude_unset`); delete → `204`.

---

## 4. Pagination, filtering & sorting (§14)

Seed a few books, then page/filter/sort:
```bash
for i in 1 2 3; do
  curl -s -X POST $BASE/books -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
    -d "{\"title\":\"Book $i\",\"author\":\"Ada Lovelace\",\"year\":$((2000+i)),\"price\":$((10*i))}" > /dev/null
done
curl -s -X POST $BASE/books -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"title":"Other","author":"Someone Else","year":1999,"price":5}' > /dev/null

# Filter by author (case-insensitive substring) + page of 2 + sort by year asc:
curl -s "$BASE/books?author=lovelace&limit=2&sort_by=year&order=asc" -H "Authorization: Bearer $ACCESS" | jq
```
**Expect:** a `Page` envelope — `{"items":[…2 books…],"total":3,"limit":2,"offset":0}`. `total` counts all matches (3), `items` is just this page (2).

```bash
# Invalid limit is rejected by the dependency:
curl -s "$BASE/books?limit=999" -H "Authorization: Bearer $ACCESS" | jq   # → 422 (le=100)
```

---

## 5. Consistent error shape (§11)

Every failure is `{"error":{"code","message","request_id"}}`:
```bash
curl -s $BASE/books/00000000-0000-0000-0000-000000000000 -H "Authorization: Bearer $ACCESS" | jq  # 404 not_found
curl -s $BASE/books/not-a-uuid -H "Authorization: Bearer $ACCESS" | jq                              # 422 validation_error
curl -s $BASE/auth/me | jq                                                                          # 401 http_error
```
**Expect:** codes `not_found`, `validation_error`, `http_error` respectively — same shape each time, each with a `request_id`.

---

## 6. Middleware headers (§12)

```bash
curl -s -D - -o /dev/null $BASE/books -H "Authorization: Bearer $ACCESS" | grep -i -E "x-request-id|x-process-time"
```
**Expect:** both `x-request-id:` and `x-process-time-ms:` headers on the response. Send your own to see it echoed:
```bash
curl -s -D - -o /dev/null -H "X-Request-ID: my-trace-123" -H "Authorization: Bearer $ACCESS" $BASE/books | grep -i x-request-id
```
**Expect:** `x-request-id: my-trace-123` (a client/proxy id flows through).

---

## 7. Lifespan (§13)

Watch the **server terminal**:
- On start you see `starting up`.
- Press `Ctrl+C` to stop → you see `shut down — engine disposed` (the DB pool closed cleanly).

**✅ Proves:** startup/shutdown run through the `lifespan` context manager.

---

## 8. Rate limiting (§16)

`/auth/login` is capped at **5/minute** per IP. Trip it:

> If you just ran §1, wait ~60s first — those earlier logins already count toward the limit.
```bash
for i in $(seq 1 6); do
  printf "attempt $i: "
  curl -s -o /dev/null -w "%{http_code}\n" -X POST $BASE/auth/login -d "username=nobody@example.com&password=wrong"
done
```
**Expect:** the first 5 → `401`, the **6th → `429`**. Confirm the shape:
```bash
curl -s -X POST $BASE/auth/login -d "username=nobody@example.com&password=wrong" | jq   # {"error":{"code":"rate_limited",...}}
```
(Wait ~1 minute for the window to reset.)

---

## 9. Structured JSON logging (§17)

Trigger a failed login, then look at the **server terminal**:
```bash
curl -s -o /dev/null -X POST $BASE/auth/login -d "username=ghost@example.com&password=wrong"
```
**Expect** a JSON log line like:
```json
{"level": "WARNING", "logger": "app", "message": "auth failed: bad login for ghost@example.com", "request_id": "…", "user_id": null}
```
Make an authenticated request and note the log line carries a non-null `user_id` and a `request_id` matching the `X-Request-ID` header from §6.

**✅ Proves:** logs are structured JSON, stamped with per-request context.

---

## 10. Environment-gated docs (§18)

In `dev` (default), docs are on:
```bash
curl -s -o /dev/null -w "dev /docs: %{http_code}\n" http://localhost:8000/docs        # → 200
```
Restart the server as `prod` and re-check:
```bash
# stop the server, then:
ENVIRONMENT=prod uv run uvicorn src.main:app
curl -s -o /dev/null -w "prod /docs: %{http_code}\n" http://localhost:8000/docs        # → 404
curl -s -o /dev/null -w "prod /openapi.json: %{http_code}\n" http://localhost:8000/openapi.json  # → 404
```
**✅ Proves:** the interactive API surface is hidden outside dev. (Restart back in `dev` afterward.)

---

## 11. RBAC — admin (§19)

Some routes (`GET /auth/{user_id}`, `GET /activity`) need an **admin**. There is **no API to
register as admin** — that would be a privilege-escalation hole. Admins are promoted
server-side, out of band.

### How to make an email an admin

Register the user normally first, then promote by email with the helper script:

```bash
# Grant admin:
uv run python scripts/make_admin.py alice@example.com
# → "Granted admin for alice@example.com."

# Revoke admin:
uv run python scripts/make_admin.py alice@example.com --revoke
```

The script ([`scripts/make_admin.py`](../scripts/make_admin.py)) flips the `is_admin` column
in Postgres. (Emails are stored lowercased, so it lowercases the argument for you. If the
user isn't registered yet, it tells you to register them first.)

**Prefer raw SQL?** Same effect:
```bash
psql "$DATABASE_URL" -c "UPDATE \"user\" SET is_admin = true WHERE email = 'alice@example.com';"
```
> `"user"` must be quoted — it's a reserved word in Postgres.

### Verify the gate

```bash
MY_ID=$(curl -s $BASE/auth/me -H "Authorization: Bearer $ACCESS" | jq -r .id)
curl -s $BASE/auth/$MY_ID -H "Authorization: Bearer $ACCESS" | jq        # non-admin → 403 forbidden
# ...run make_admin.py for your email, then retry (no re-login needed):
curl -s $BASE/auth/$MY_ID -H "Authorization: Bearer $ACCESS" | jq        # admin → 200
```
**Expect:** `403` (`"code":"forbidden"`) before, `200` after. No new token needed —
`require_admin` reads `is_admin` **fresh from the DB** on each request, so promotion takes
effect immediately.

> For how this is done in real production systems (role tables, IdP groups, JIT elevation),
> see the design discussion in [`boilerplate_guide.md`](./boilerplate_guide.md) §19.

---

## 12. Secrets (§20)

```bash
git check-ignore .env        # → prints ".env"  (it is gitignored)
git ls-files | grep -E '(^|/)\.env$' || echo "OK: .env is NOT tracked"
python -c "import secrets; print(secrets.token_urlsafe(64))"   # generate a fresh JWT_SECRET_KEY
```
**Rotation drill:** change `JWT_SECRET_KEY` in `.env`, restart, and re-run any `Authorization: Bearer $ACCESS` call → `401` (all old tokens are now invalid; log in again). Full steps: [`secrets_runbook.md`](./secrets_runbook.md).

---

## 13. Run the test suite (§15)

```bash
uv sync --group dev      # first time: pytest, pytest-asyncio, httpx, aiosqlite
uv run pytest -q         # → all passing (no server / no Postgres needed)
uv run pytest tests/test_auth.py -v    # watch individual auth/rate-limit/admin cases
```
**✅ Proves:** the whole app is exercised in-process via `httpx.AsyncClient` + `dependency_overrides` (in-memory SQLite DB, fake auth).

---

## 14. MongoDB activity log (§21)

The app writes an audit event to **MongoDB** on `login`, `login_failed`, and `book_created`,
and exposes them at `GET /activity` (admin-only). This is the NoSQL / polyglot-persistence piece.

### Set up MongoDB locally with Docker

You don't need to install MongoDB — run it in a container.

```bash
# Start a Mongo container (data persists in the named volume across restarts):
docker run -d --name bp-mongo -p 27017:27017 -v bp-mongo-data:/data/db mongo:7

# Verify it's up:
docker ps --filter name=bp-mongo                 # should be "Up"
docker exec bp-mongo mongosh --quiet --eval 'db.runCommand({ ping: 1 })'   # → { ok: 1 }
```

That's it — the app's default `MONGO_URL=mongodb://localhost:27017` already points at it, so
no config change is needed. Restart the API server and you should see `mongo connected` in its logs.

Handy container commands:
```bash
docker stop bp-mongo        # pause it
docker start bp-mongo       # resume (data is still there)
docker rm -f bp-mongo       # remove it; add `docker volume rm bp-mongo-data` to wipe data too
# peek at the stored events directly:
docker exec bp-mongo mongosh bookstore --quiet --eval 'db.activity.find().sort({ts:-1}).limit(3)'
```
> The app boots fine **without** Mongo — activity writes are best-effort — but the feed will be empty.

**Generate some events, then read them** (needs an **admin** token — see §11):
```bash
# these actions each record an event:
curl -s -X POST $BASE/auth/login -d "username=alice@example.com&password=supersecret123" > /dev/null   # "login"
curl -s -X POST $BASE/books -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"title":"Event Source","author":"A B","year":2024,"price":10}' > /dev/null                      # "book_created"

# read the audit feed (admin only):
curl -s "$BASE/activity?limit=5" -H "Authorization: Bearer $ACCESS" | jq
```
**Expect:** a `Page` of events, newest first, e.g.
```json
{ "items": [
    {"type":"book_created","user_id":"…","detail":{"book_id":"…","title":"Event Source"},"ts":"…"},
    {"type":"login","user_id":"…","detail":{},"ts":"…"} ],
  "total": 2, "limit": 5, "offset": 0 }
```
**✅ Proves:** two databases running side by side — Postgres for entities, Mongo for the
event stream — and that different event types carry different `detail` shapes (why it's NoSQL).

As a non-admin, `GET /activity` → `403` (same RBAC gate as §11). Tear down: `docker stop bp-mongo`.

---

## Feature checklist

Tick these off as you go:

- [ ] Register → login → `/auth/me` → refresh (rotation) → logout (§1)
- [ ] Refresh-token **reuse** is rejected (§1d)
- [ ] Validation `422`s: short password, password-contains-username, bad email (§2)
- [ ] Book create collapses whitespace; update is partial; delete `204` (§3)
- [ ] `Page` envelope with filter + limit + sort; bad `limit` → `422` (§4)
- [ ] Error shape identical for `404` / `422` / `401` (§5)
- [ ] `X-Request-ID` + `X-Process-Time-ms` headers; client id echoes (§6)
- [ ] `starting up` / `shut down` lifespan logs (§7)
- [ ] 6th login in a minute → `429` (§8)
- [ ] Failed login emits a JSON log line with `request_id` (§9)
- [ ] `/docs` = `200` in dev, `404` in prod (§10)
- [ ] `/auth/{id}` → `403` as user, `200` as admin (§11)
- [ ] `.env` gitignored; key rotation invalidates tokens (§12)
- [ ] `pytest` green (§13)
- [ ] `/activity` shows login + book_created events; `403` as non-admin (§14)

---

*Evolving doc. When you add an endpoint or feature, add a numbered test block (command →
expected → what it proves), a row to the topics table, and a checklist item — mirroring a
new section in [`boilerplate_guide.md`](./boilerplate_guide.md).*
