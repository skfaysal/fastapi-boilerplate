# FastAPI Mastery Roadmap — Path to AI Engineer / AI System Architect

## How much FastAPI do you actually need?

Enough to be "production-dangerous," not framework-expert. For an AI engineer/architect role, FastAPI is the **chassis** — maybe 25% of the job. The other 75% is what you bolt onto it: auth, resilience, streaming, observability, queues, vector stores, and LLM orchestration. Employers don't hire "FastAPI experts," they hire people who can design a system where FastAPI is one correct choice among many. So this roadmap treats FastAPI depth as Phases 1-2, and the AI/systems-architecture layer (Phases 3-5) as the actual destination.

## Where you are right now

Your [fastapi-boilerplate](../src) already has some genuinely production-grade pieces most tutorials skip:
- Access/refresh JWT split with **rotation + reuse detection** ([service.py](../src/auth/service.py)) — this is the same pattern real auth systems use (Auth0, Supabase).
- Timing-attack mitigation in login (`authenticate` runs a dummy hash on unknown emails).
- Async SQLModel + Alembic migrations, layered router → dependency → service → model.
- A written design doc for *why* ([jwt_auth.md](jwt_auth.md)), not just what.

What's missing (and it's a lot — this is normal at this stage): tests, rate limiting, structured logging/observability, background task queues, caching, containerization, CI, and anything AI/LLM-specific. That gap is exactly this roadmap.

---

## Phase 1 — Core FastAPI you haven't touched yet

**Topics to master**
- Pydantic v2 validators (`field_validator`, `model_validator`), custom base models for consistent serialization
- Dependency injection beyond DI: dependencies as reusable validation/authorization gates, dependency caching within a request
- Exception handling: custom `@app.exception_handler`, consistent error response schema
- Middleware: request ID injection, timing, custom CORS
- API versioning strategy, pagination/filtering/sorting conventions
- `lifespan` context manager for startup/shutdown (replacing ad hoc engine creation)
- Testing: `httpx.AsyncClient` + `ASGITransport`, `dependency_overrides` for mocking auth/db in tests

**Experiments in this project**
1. Add a `tests/` dir with pytest-asyncio; write tests for `/auth/login`, `/auth/refresh` reuse-detection, and `/books` auth-gating using `dependency_overrides` instead of a real DB.
2. Move `async_engine`/`session_factory` creation ([db/main.py](../src/db/main.py)) into a `lifespan` handler in [main.py](../src/main.py); turn off `echo=True` outside dev via `Config`.
3. Add a global exception handler so every error (validation, HTTPException, unhandled) returns one consistent JSON shape (`{"error": {"code", "message"}}`).
4. Add a `Book` list endpoint with pagination (`limit`/`offset` or cursor) and a `field_validator` on `UserCreate` for password strength.
5. Add `/health` and `/health/db` (checks a real DB round-trip) endpoints — required by every deployment platform and load balancer.

---

## Phase 2 — Production hardening & security

**Topics to master**
- Rate limiting (token bucket, Redis-backed — e.g. `slowapi`)
- Secrets management (never in `.env` committed; per-environment secrets, rotation)
- CORS configured explicitly, not wildcarded
- Hiding `/docs` and `/redoc` outside dev
- Structured logging (JSON logs) with per-request context (request id, user id) — not `print`/default logging
- RBAC / permission dependencies beyond "is authenticated"
- Secure cookie option for refresh tokens (httponly, secure, samesite) as an alternative to bearer-in-body
- Password/token brute-force protection, account lockout

**Experiments in this project**
1. Add `slowapi` rate limiting on `/auth/login` and `/auth/refresh` (the two endpoints your own [jwt_auth.md](jwt_auth.md) design notes flag as brute-forceable).
2. Add structured JSON logging middleware that stamps every log line with a request id and (if present) `user.id`; log every auth failure.
3. Gate `/docs`, `/redoc`, `/openapi.json` behind `Config.ENVIRONMENT == "dev"`.
4. Add a simple role field to `User` (`is_admin`) and a `require_admin` dependency; protect `GET /auth/{user_id}` with it (right now any authenticated user can look up any other user by id — that's an authorization gap worth fixing as the exercise).
5. Move `JWT_SECRET_KEY` generation/rotation into a documented runbook; verify `.env` is gitignored (it already is, but write the rotation steps down).

---

## Phase 3 — Scalability & systems architecture

**Topics to master**
- Connection pooling tuning (pool size, `pool_pre_ping`) for async SQLAlchemy under load
- Caching (Redis) — cache-aside pattern, invalidation
- Background task queues: `BackgroundTasks` (fire-and-forget, <1s only) vs Celery/Arq/RQ (durable, retryable) — know when each is wrong
- Retry/backoff (`tenacity`), timeouts, and circuit breakers for any outbound call (DB, third-party API, later: LLM)
- Repository pattern vs "service does DB access directly" — when the extra layer earns its keep
- Containerization (Docker, multi-stage builds), docker-compose for local Postgres+Redis
- CI (GitHub Actions: lint, type-check, test, build image)

**Experiments in this project**
1. Add Redis via docker-compose; cache `GET /books` and `GET /auth/{id}` with a short TTL, invalidate on write.
2. Introduce Arq (lightweight, async-native) for one real async job — e.g., "send welcome email on register" — instead of a fire-and-forget `BackgroundTasks` call, specifically to feel the durability difference.
3. Wrap the DB session dependency with `tenacity` retry on transient connection errors; add a request timeout middleware.
4. Write a multi-stage `Dockerfile` (build deps with `uv`, slim runtime image) and a `docker-compose.yml` (app + postgres + redis).
5. Add a GitHub Actions workflow: `ruff check`, `pytest`, build the Docker image on every PR.

---

## Phase 4 — AI/agentic backend layer (the differentiator)

**Topics to master**
- Streaming responses: Server-Sent Events (SSE) for token-by-token LLM output vs WebSockets for bidirectional agent chat
- Async LLM client integration: never block the event loop on a blocking SDK call — use async clients or `run_in_threadpool`
- LLM resilience: per-call retry + exponential backoff, multi-provider fallback (if model A fails, rotate to model B), total-timeout budget
- Conversation/session state persistence (Postgres) so an agent survives a server restart
- Vector search (pgvector) for RAG: embeddings, similarity search, chunking strategy
- Long-term memory pattern (e.g., mem0-style: extract facts, embed, retrieve per-user)
- Tool calling / function calling from an LLM, and validating tool arguments with Pydantic before executing them
- LLM observability: tracing prompts/completions/tokens/cost (Langfuse or similar), separate from your general app logs
- Guardrails: input validation against prompt injection, output validation before executing agent-suggested actions, cost/rate caps per user
- Model Context Protocol (MCP) — the emerging standard for exposing tools/context to agents; worth knowing conceptually even before adopting it

**Experiments in this project**
1. Add a new `src/chat/` module: a minimal endpoint that calls an LLM API and streams the response back via SSE — your first taste of the async-streaming pattern, in your existing auth-protected router style.
2. Persist conversations: a `Conversation`/`Message` SQLModel table (mirrors how you built `RefreshToken`), so a chat survives a restart — reuse the exact async session + service-layer pattern you already have.
3. Wrap the LLM call in `tenacity` retry + a second fallback model, with a total timeout budget — apply the Phase 3 resilience lesson to a real LLM call.
4. Add `pgvector` to Postgres (extension), embed and store `Book` descriptions, and add a `POST /books/search` semantic-search endpoint — RAG in miniature, using data you already have.
5. Add basic LLM call tracing: log prompt tokens, completion tokens, latency, and cost estimate per call, tagged with `user.id` and `request_id` (reuse Phase 2's structured logging).
6. Add a per-user rate/cost cap dependency (e.g., "max N LLM calls per day") — combine Phase 2 rate limiting with an AI-specific cost-control concern.

---

## Phase 5 — Capstone: system-architect thinking

By now the topics are learned in isolation. The capstone is proving you can reason about tradeoffs, not just implement:

1. Write an ADR (architecture decision record) in `docs/adr/` for one real decision you made in Phases 1-4 (e.g., "why SSE over WebSockets for chat," or "why Arq over Celery here") — practice the artifact architects actually produce.
2. Draw (and write up) the full request path for your `/chat` endpoint end to end: client → rate limiter → auth → router → service → LLM client (with fallback) → DB persistence → SSE stream back. Identify every failure point and what happens at each one.
3. Load-test `/books` and `/chat` (e.g., with `locust` or `hey`) and use the results to justify a real tuning decision (pool size, cache TTL, worker count) instead of guessing.
4. Take one existing security assumption in [jwt_auth.md](jwt_auth.md) (e.g., "access tokens can't be revoked early") and write down what you'd change if a real incident forced it (e.g., a short-lived denylist in Redis) — architects reason about tradeoffs, not just implement the happy path.

---

## Suggested pacing

- Phase 1-2: 2-3 weeks (you already know ~40% of this from the auth work)
- Phase 3: 2 weeks
- Phase 4: 3-4 weeks — this is the part that actually differentiates "AI engineer" from "backend developer"
- Phase 5: ongoing, revisit after each phase

## Sources consulted

- [FastAPI Best Practices (zhanymkanov)](https://github.com/zhanymkanov/fastapi-best-practices)
- [Production-ready FastAPI + LangGraph agent template](https://github.com/wassim249/fastapi-langgraph-agent-production-ready-template)
- [Architecting Scalable FastAPI Systems for LLM Applications](https://medium.com/@moradikor296/architecting-scalable-fastapi-systems-for-large-language-model-llm-applications-and-external-cf72f76ad849)
- [Building Production-Ready Agentic AI Systems with Docker and FastAPI](https://medium.com/@er.rajkumaar/building-production-ready-agentic-ai-systems-with-docker-and-fastapi-b4c2231b3945)
- [A Practical Guide to FastAPI Security](https://davidmuraya.com/blog/fastapi-security-guide/)
- [FastAPI official: OAuth2 + JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
