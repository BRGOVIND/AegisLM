# RedForge Security Hardening Status

_Last updated: 2026-06-16_

This document records what security hardening is already in place so a future
security audit does not re-implement things that exist and can focus on the
genuine gaps listed at the bottom.

---

## Already Implemented

### HTTP Security Headers (`backend/app/main.py`)

`SecurityHeadersMiddleware` (Starlette `BaseHTTPMiddleware`) is applied to
**every response** — including API routes, the root endpoint, and error
responses:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `1; mode=block` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` _(non-localhost only)_ |

### CORS (`backend/app/main.py`)

- Origins restricted via `REDFORGE_ALLOWED_ORIGINS` env var (default: `http://localhost:5173,http://127.0.0.1:5173`).
- Methods restricted to: `GET POST PUT DELETE OPTIONS` (no wildcard).
- Headers restricted to: `Content-Type Authorization Accept X-Requested-With` (no wildcard).
- `allow_credentials=True` (cookies scoped to allowed origins only).

### Input Validation

- FastAPI/Pydantic models enforce required fields and types on all POST bodies (`422` on malformed input).
- Unknown `agent_run_id` returns `404` (not 500).
- Non-JSON `Content-Type` on POST endpoints returns `422`/`415`.

### Test Coverage

12 tests in `backend/tests/test_security.py` verify:
- All 5 security headers present on both root and API routes.
- CORS: allowed origin receives `Access-Control-Allow-Origin`; unknown origin does not.
- Input validation: missing required field → 422; 404 for nonexistent resource; bad Content-Type → error.

---

## Known Gaps (for the upcoming audit)

These are **not yet addressed** — the audit should focus here:

1. **Input size caps** — No max body size or prompt length limit. A single request with a multi-MB prompt would be accepted.
2. **model_name / SSRF validation** — `model_name` in agent/benchmark requests is passed directly to Ollama's HTTP API. A malicious value like `http://internal-service` could potentially be used for SSRF.
3. **Rate limiting** — No per-IP or per-endpoint rate limiting. The `/api/agent` endpoint launches background tasks with no throttle.
4. **Frontend XSS** — `model_response` and `attack_prompt` content from the DB is rendered in the React UI. Ensure DOMPurify or equivalent is sanitizing LLM output before rendering.
5. **Auth / API key** — No authentication on any endpoint. All routes are publicly accessible.
6. **Dependency audit** — `pip audit` / `npm audit` not run recently.
7. **SQL injection** — SQLAlchemy ORM used throughout (parameterised), but raw `text()` calls in a few places warrant review.
