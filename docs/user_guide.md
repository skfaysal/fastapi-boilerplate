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
docker compose up -d                      # Postgres + MongoDB + Kafka (see §22)
uv sync                                   # install deps
cp .env.example .env                      # then edit: set DATABASE_URL + JWT_SECRET_KEY
uv run alembic upgrade head               # build schema (incl. is_admin column)
uv run uvicorn src.main:app --reload      # → http://localhost:8000
uv run python -m src.activity.consumer    # separate terminal — Kafka → Mongo writer (§22)
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
| Kafka-backed activity pipeline (§22) | producer → topic → consumer → Mongo | [15](#15-kafka-backed-activity-pipeline-22) |

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

The app writes an audit event on `login`, `login_failed`, and `book_created`, and exposes
them at `GET /activity` (admin-only). This is the NoSQL / polyglot-persistence piece — Postgres
stays the source of truth for entities (users, books), Mongo only holds this append-only event feed.

Since §22, the request path never writes to Mongo directly — it publishes to **Kafka**, and a
separate consumer process does the actual Mongo insert. See §22 for the infrastructure and the
full producer → topic → consumer walkthrough; this section is about the *read* side and the
event shape, which are unchanged by that move.

**Generate some events, then read them** (needs an **admin** token — see §11, and the consumer
from §22 running so events actually reach Mongo):
```bash
# these actions each publish an event (to Kafka — see §22 to have them land in Mongo):
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

As a non-admin, `GET /activity` → `403` (same RBAC gate as §11).

---

## 15. Kafka-backed activity pipeline (§22)

```
auth/router.py, books/router.py        (login, login_failed, book_created)
        │
        │  activity.record(type, user_id, detail)
        ▼
activity/service.py                     PRODUCER — publishes, never touches Mongo
        │
        │  send_and_wait()
        ▼
Kafka topic "activity-events"           (src/kafka.py — broker + topic config)
        │
        │  consumed by group "activity-mongo-writer"
        ▼
activity/consumer.py                    CONSUMER — separate process
        │
        │  insert_one(event); commit offset only after this succeeds
        ▼
MongoDB "activity" collection
        │
        │  find().sort(ts, -1)
        ▼
activity/router.py                      GET /activity (admin-only) — reads Mongo, never touches Kafka
```

**Which endpoints produce, and when the consumer picks it up:**

- `POST /auth/login` produces a `login` event on success or a `login_failed` event on bad
  credentials. `POST /books` produces a `book_created` event. In all three cases, the producer
  call (`activity.record(...)` → Kafka `send_and_wait`) happens **inside the request** — it's the
  last thing the endpoint does before returning the HTTP response, and the response does not wait
  on Mongo at all, only on Kafka accepting the message.
- The consumer runs in a **separate, always-running process** (`uv run python -m
  src.activity.consumer`), not inside the request and not triggered by it. It's continuously
  polling the `activity-events` topic in the background; whenever a new message appears, it picks
  it up — could be milliseconds after the endpoint published it, or later if the consumer was
  briefly down (Kafka just holds the message until something in the `activity-mongo-writer` group
  reads it). Only at that point, in that separate process, does the event actually get
  `insert_one`'d into Mongo. The API request that produced the event has already finished and
  returned long before this happens.

| File | Role | Does with the data |
|---|---|---|
| `auth/router.py`, `books/router.py` | caller | fires `activity.record(...)` on login / login_failed / book_created |
| `src/activity/service.py` | **producer** | serializes the event, publishes it to the `activity-events` topic — never touches Mongo |
| `src/kafka.py` | broker client | producer + consumer config, topic name, nothing else |
| `src/activity/consumer.py` | **consumer** (separate process, group `activity-mongo-writer`) | reads the topic, `insert_one`s each event into Mongo, commits the offset only after that write succeeds |
| MongoDB `activity` collection | store | holds what the consumer wrote — the only thing `GET /activity` ever reads |
| `src/activity/router.py` | reader | `GET /activity` reads Mongo directly — it never touches Kafka |

One producer, one topic, one consumer group today — the point of the topic existing at all is
that more consumers (fraud detection, notifications) could subscribe later without changing
`auth/router.py` or `books/router.py`.

### 1. Start the infrastructure

All three datastores (Postgres, MongoDB, Kafka) now come from one Compose file:

```bash
docker compose up -d
docker compose ps     # bp-postgres, bp-mongo, bp-kafka — all "Up"
```

`docker-compose.yml` reuses the **same named volumes** the standalone Postgres/Mongo containers
already had (`postgres_data`, `bp-mongo-data`, marked `external: true` in the compose file) — so
switching to Compose does not lose any existing data. Kafka is a fresh single-node, KRaft-mode
broker (no Zookeeper) — fine for local/dev; a real deployment would run multiple brokers with a
replication factor above 1.

```bash
# Confirm the broker is actually accepting connections:
docker exec bp-kafka /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092
```

### 2. Start the API and the consumer (two separate processes)

```bash
uv run uvicorn src.main:app --reload        # terminal 1 — the API (Kafka producer lives inside it)
uv run python -m src.activity.consumer      # terminal 2 — Kafka → Mongo writer
```

You should see `kafka producer started` in the API's startup logs (right after `mongo connected`),
and `started — topic=activity-events group=activity-mongo-writer` from the consumer.

**Why a separate process for the consumer**, not a background task inside the API: it decouples
the Mongo writer's lifecycle from the API's. Either can crash, restart, or (in a real deployment)
scale independently, without the other noticing — the same shape a production consumer worker
would have. This is the one piece of this repo that is *not* just `uv run uvicorn` — treat it
like any other required process (a systemd unit, a k8s Deployment, a `Procfile` entry).

### 3. Watch an event flow through, end to end

```bash
# 1. trigger a login — the API publishes to Kafka and returns immediately, not waiting on Mongo:
curl -s -X POST $BASE/auth/login -d "username=alice@example.com&password=supersecret123" > /dev/null

# 2. peek at the raw Kafka message (bypassing the consumer, to see the wire format):
docker exec bp-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic activity-events --from-beginning --max-messages 1

# 3. give the consumer a moment, then check Mongo has it:
docker exec bp-mongo mongosh bookstore --quiet --eval 'db.activity.find().sort({ts:-1}).limit(1)'

# 4. and the API's own read path agrees:
curl -s "$BASE/activity?limit=1" -H "Authorization: Bearer $ACCESS" | jq
```
**Expect:** the same event — same `type`, `user_id`, `ts` — visible at all three layers (raw
Kafka message, raw Mongo document, `GET /activity` response). The `ts` you see in the raw Kafka
message is an ISO **string** (JSON has no datetime type); the consumer converts it back into a
real datetime before inserting, so it stores as a proper Mongo date, indistinguishable from the
events written before Kafka existed — `sort` keeps working correctly across old and new documents.

### 4. Prove the decoupling actually works

```bash
docker compose stop mongo
curl -s -o /dev/null -w "login while mongo is down: %{http_code}\n" \
  -X POST $BASE/auth/login -d "username=alice@example.com&password=supersecret123"
docker compose start mongo
```
**Expect:** still `200`/`401` as normal (whatever the credentials deserve), with **no added
latency** — the login request never touches Mongo at all anymore, only Kafka. Compare this to
the pre-Kafka design, where a Mongo outage added up to 3 seconds to every request that recorded
an event. Once Mongo is back and the consumer reconnects, it resumes from its last committed
offset — the events published while Mongo was down are still in Kafka and get written once
the consumer catches up. Nothing is lost.

**✅ Proves:** the request path is now fully decoupled from Mongo's availability, and events are
durable (replayable from Kafka) instead of best-effort-and-gone.

### Design notes (why it's built this way)

- **Delivery is at-least-once, not exactly-once.** The consumer commits its Kafka offset only
  *after* the Mongo write succeeds (`enable_auto_commit=False` in `src/kafka.py`), so a crash
  mid-processing re-delivers the event on restart — a possible duplicate document, never a silent
  loss. Acceptable for an audit log; would need an idempotency key if this fed something
  duplicate-sensitive (e.g. billing).
- **A permanently-failing message doesn't wedge the consumer.** `src/activity/consumer.py` retries
  the Mongo write 3 times with backoff; if it still fails, the event is logged loudly
  (`logger.error`) and dropped, and the offset still advances — a poison message can't block
  every event behind it forever.
- **The producer is best-effort, matching the original Mongo design.** If Kafka itself is
  unreachable at startup, the app still boots (`start_producer()` failure is caught in
  `src/main.py`'s lifespan, same pattern as Mongo) and `record()` just logs a warning and drops
  the event rather than raising into the request.
- **Events are keyed by `user_id`** when publishing (`src/activity/service.py`), so Kafka
  guarantees all of one user's events land in the same partition in the order they were
  produced — relevant once there's more than one partition.

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
- [ ] `docker compose up -d` brings up Postgres + Mongo + Kafka; existing data intact (§22)
- [ ] Login while Mongo is stopped still returns instantly (no timeout) — proves the Kafka decoupling (§22)

---

*Evolving doc. When you add an endpoint or feature, add a numbered test block (command →
expected → what it proves), a row to the topics table, and a checklist item — mirroring a
new section in [`boilerplate_guide.md`](./boilerplate_guide.md).*
