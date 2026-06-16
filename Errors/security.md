# AcademicOS — Security Audit Report

**Audit date:** 2026-06-14
**Branch audited:** `claude/awesome-tesla-vcav82`
**Scope:** Full codebase — FastAPI backend (`backend/main.py`), Next.js frontend (`frontend/`), agents (`agents/`), ingestion (`ingestion/`), configuration (`config/`), schemas, scripts, CI/deploy config, dependencies.
**Threat model:** Application deployed to the public internet; attacker has full knowledge of the source.

---

## Executive Summary

AcademicOS is a **single-tenant application with no authentication, authorization, or session-identity layer of any kind.** The backend exposes a fully public read/write REST API, and the launch script binds it to `0.0.0.0`. If deployed to the public internet as the task assumes, **every endpoint — including all write endpoints — is reachable and usable by any anonymous attacker on the planet.** This single design choice is the root of most Critical/High findings below and effectively collapses confidentiality and integrity for all stored data.

The good news: the code is disciplined about **SQL parameterization** (no SQL injection found) and the React frontend does **not** use `dangerouslySetInnerHTML` (no obvious stored XSS sink). The vulnerabilities are overwhelmingly in the **access-control, transport, hardening, and operational** layers rather than in classic injection.

| ID | Title | Severity |
|----|-------|----------|
| AOS-001 | Complete absence of authentication on all API endpoints | Critical |
| AOS-002 | No authorization / broken access control — anonymous write access | Critical |
| AOS-003 | API bound to `0.0.0.0` with no auth, exposing all interfaces | High |
| AOS-004 | Insecure Direct Object Reference across all object IDs | High |
| AOS-005 | Telegram bot has no sender authorization (data exfiltration) | High |
| AOS-006 | No rate limiting / brute-force / DoS protection | High |
| AOS-007 | Unbounded `limit` / resource-exhaustion query amplification | Medium |
| AOS-008 | Missing security headers (CSP, X-Frame-Options, HSTS, nosniff) | Medium |
| AOS-009 | Third-party CDN asset loaded `@latest` without SRI | Medium |
| AOS-010 | No transport security (HTTP, plaintext API base URL) | Medium |
| AOS-011 | Unvalidated `answer_image_path` stored from client (path injection) | Medium |
| AOS-012 | Business-logic / data-integrity gaps (cross-paper writes) | Medium |
| AOS-013 | Error / exception detail leakage to clients and logs | Low |
| AOS-014 | CORS configuration hardcoded & likely to be loosened to `*` | Low |
| AOS-015 | Dependency currency / supply-chain monitoring gap | Low |
| AOS-016 | Hardcoded developer absolute path in launch script | Low |
| AOS-017 | Sensitive identifiers written to logs / stdout | Informational |

---

## AOS-001 — Complete absence of authentication on all API endpoints

### Severity
Critical

### CWE Category
CWE-306: Missing Authentication for Critical Function

### OWASP Category
A07:2021 — Identification and Authentication Failures (also A01:2021 — Broken Access Control)

### Location
`backend/main.py` — entire file. All route decorators (`/api/health`, `/api/papers`, `/api/papers/{id}/questions`, `/api/questions/{id}`, `/api/dashboard`, `/api/sessions`, `/api/sessions/{id}/questions/{qid}`, `/api/sessions/{id}/complete`, `/api/attempts`, `/api/weaknesses`, `/api/status`, `/api/coverage`, `/api/briefing`, `/api/analytics`).

### Vulnerability Description
There is no authentication mechanism anywhere in the application. A repository-wide search for `auth`, `login`, `password`, `jwt`, `token`, `Depends(`, `bearer`, or any auth middleware returns **zero** results in the backend other than the route decorators themselves. The FastAPI app registers no security dependency, no API key check, no session cookie, no OAuth. Every endpoint — read **and** write — answers any unauthenticated request.

### Attack Scenario
1. Attacker discovers the public API host (e.g. `https://api.academic-os.example`).
2. Attacker issues `GET /api/dashboard`, `GET /api/weaknesses`, `GET /api/analytics` and immediately receives the student's full academic profile, weaknesses, confidence-calibration, notes, and study history.
3. Attacker issues `POST /api/attempts`, `POST /api/sessions`, `POST /api/sessions/{id}/complete` and writes arbitrary records, corrupting the mastery model and spaced-repetition state (`_update_mastery` mutates `progress.db`).

### Impact
- **Confidentiality:** Total exposure of all stored data, including free-text `notes` the student writes per question attempt (potential PII).
- **Integrity:** Any attacker can create/modify/complete sessions and attempts, and trigger writes to `progress.db` mastery state.
- **Availability/Compliance:** Combined with no rate limiting (AOS-006), trivial abuse; if any real student PII is stored, this is a reportable breach under GDPR.

### Evidence
```python
# backend/main.py
app = FastAPI(title="AcademicOS API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[...], allow_credentials=False, ...)

@app.post("/api/attempts")
def create_attempt(body: AttemptCreate) -> dict:   # no auth dependency
    ...
```
Grep across `backend/` for `Depends(` returns only route decorators — no security dependencies exist.

### Reproduction Steps
1. Start the backend (`./start-backend.sh`).
2. From any machine: `curl http://<host>:8000/api/dashboard` → returns full data with no credentials.
3. `curl -X POST http://<host>:8000/api/attempts -H 'Content-Type: application/json' -d '{"question_id":1,"marks_awarded":0,"marks_available":1,"confidence":1}'` → record created, mastery mutated.

### Recommended Fix
- Introduce an authentication layer before any public deployment: a FastAPI security dependency (`Depends(get_current_user)`) on every non-health route, backed by signed session cookies or OAuth/OIDC.
- Even for a single-user app, require at minimum a server-side API key / bearer token loaded from the environment and validated on every request.
- Default-deny: add a global dependency so new routes are protected unless explicitly opted out.

### Confidence
High

### Exploitability
High

---

## AOS-002 — No authorization / broken access control (anonymous write access)

### Severity
Critical

### CWE Category
CWE-862: Missing Authorization

### OWASP Category
A01:2021 — Broken Access Control

### Location
`backend/main.py` — all mutating endpoints: `POST /api/sessions` (758), `PATCH /api/sessions/{id}/questions/{qid}` (781), `POST /api/sessions/{id}/complete` (802), `POST /api/attempts` (884).

### Vulnerability Description
Even setting authentication aside, there is no ownership or role model. The data model (`schemas/attempts.sql`, `progress.sql`) has no `user_id`/`owner` column, so there is no notion of "whose session" or "whose attempt." Any caller may mutate any record. There is no admin/user separation, no RBAC, and no resource-ownership check anywhere.

### Attack Scenario
An attacker (or any other tenant, if the app is ever multi-user) calls `POST /api/sessions/{id}/complete` for an arbitrary `session_id`, marking another student's session complete, or floods `POST /api/attempts` to poison the mastery/spaced-repetition engine so the legitimate user receives wrong revision priorities.

### Impact
Integrity of the entire learning model is unprotected. If the app is extended to multiple students on one backend, this becomes a full multi-tenant isolation failure with cross-student data tampering.

### Evidence
```python
@app.post("/api/sessions/{session_id}/complete")
def complete_session(session_id: int, body: SessionComplete) -> dict:
    cur = conn.execute("UPDATE sessions SET ended_at=?,... WHERE id=?", (...))
    # no check that the caller owns session_id
```

### Reproduction Steps
1. `curl -X POST http://<host>:8000/api/sessions/1/complete -d '{"total_time_seconds":1}' -H 'Content-Type: application/json'` completes session 1 regardless of who created it.

### Recommended Fix
- Add an `owner_id` column to `sessions`, `attempts`, `question_times`, and SR items; scope every query to the authenticated principal.
- Enforce ownership checks server-side (`WHERE id=? AND owner_id=?`) on every read and write of user-scoped data.

### Confidence
High

### Exploitability
High

---

## AOS-003 — API bound to `0.0.0.0` with no authentication

### Severity
High

### CWE Category
CWE-668: Exposure of Resource to Wrong Sphere

### OWASP Category
A05:2021 — Security Misconfiguration

### Location
`start-backend.sh:18`

### Vulnerability Description
The launch script binds Uvicorn to all network interfaces (`--host 0.0.0.0 --port 8000`). Combined with the total absence of authentication (AOS-001), this publishes the full read/write API to every network the host is attached to (LAN, cloud VPC, or the public internet if a security group/firewall is open).

### Attack Scenario
Deployed on a cloud VM with port 8000 reachable, the entire API is exposed to internet scanners (Shodan/Censys index `0.0.0.0:8000` FastAPI hosts within hours). No credentials are needed to read or write.

### Impact
Directly converts the missing-auth design flaw into a remotely exploitable exposure.

### Evidence
```bash
exec "$VENV_PYTHON" backend.main:app --host 0.0.0.0 --port 8000 "$@"
```

### Reproduction Steps
1. Run `./start-backend.sh` on a host with a public IP and open port.
2. From another network: `curl http://<public-ip>:8000/api/dashboard` succeeds.

### Recommended Fix
- Bind to `127.0.0.1` and place the API behind an authenticating reverse proxy / API gateway, **or** do not expose the port publicly until AOS-001 is fixed.
- Terminate TLS and enforce auth at the proxy.

### Confidence
High

### Exploitability
High

---

## AOS-004 — Insecure Direct Object Reference (IDOR) across all object IDs

### Severity
High

### CWE Category
CWE-639: Authorization Bypass Through User-Controlled Key

### OWASP Category
A01:2021 — Broken Access Control

### Location
`backend/main.py`: `GET /api/papers/{paper_id}/questions` (199), `GET /api/questions/{question_id}` (273), `PATCH /api/sessions/{session_id}/questions/{question_id}` (781), `POST /api/sessions/{session_id}/complete` (802), `POST /api/attempts` (session_id/question_id from body).

### Vulnerability Description
All object references are sequential integer primary keys taken directly from the URL/body and used to fetch or mutate records with no ownership scoping. Because IDs are sequential (`AUTOINCREMENT`), an attacker can enumerate the entire object space (`/api/questions/1`, `/2`, …) and read or write every record.

### Attack Scenario
Attacker scripts `for id in 1..N: GET /api/questions/$id` to dump the full question bank, mark schemes, examiner observations, and all `previous_attempts` (including student `notes`).

### Impact
Mass extraction of all content and the student's attempt history/notes; arbitrary mutation of any session/attempt.

### Evidence
```python
@app.get("/api/questions/{question_id}")
def get_question(question_id: int) -> dict:
    rows = _query(..., "WHERE q.id = ?", (question_id,))
    # returns previous_attempts incl. notes; no owner check
```

### Reproduction Steps
1. `for i in $(seq 1 1000); do curl -s http://<host>:8000/api/questions/$i; done` enumerates all questions and attached attempt notes.

### Recommended Fix
- Scope every object lookup to the authenticated owner.
- Consider opaque/UUID identifiers for user-scoped resources to resist enumeration (defense in depth, not a substitute for authorization).

### Confidence
High

### Exploitability
High

---

## AOS-005 — Telegram bot has no sender authorization (data exfiltration & abuse)

### Severity
High

### CWE Category
CWE-862: Missing Authorization

### OWASP Category
A01:2021 — Broken Access Control

### Location
`agents/delivery/telegram_agent.py:66-199` (`start_bot` and all `_cmd_*` handlers).

### Vulnerability Description
`start_bot()` registers command handlers (`/briefing`, `/status`, `/coverage`, `/quiz`, `/revise`, `/progress`) and replies to **whoever sent the message** (`update.message.reply_text(...)`). There is no check that the sender's chat/user ID equals the configured `TELEGRAM_CHAT_ID`. The bot uses long-polling, so any Telegram user who discovers the bot's @username can invoke every command. While the *daily briefing push* (`send_message`) targets the configured chat, the *interactive command handlers* do not gate the requester.

### Attack Scenario
An attacker who learns the bot handle messages it `/progress`, `/coverage`, `/briefing` and receives the student's full curriculum progress, weak topics, and academic standing — exfiltrating private academic data through the bot, bypassing even the (absent) web auth.

### Impact
Confidential academic/progress data leaks to any Telegram user; the bot can also be used as a free compute/abuse oracle (`/revise`, `/quiz` trigger DB work per request — DoS vector).

### Evidence
```python
async def _cmd_progress(update, context):
    ...
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
# no `if update.effective_chat.id != int(TELEGRAM_CHAT_ID): return`
```

### Reproduction Steps
1. Find the bot's @username.
2. Send `/progress`. The bot replies with curriculum coverage to the attacker's chat.

### Recommended Fix
- At the top of every handler, verify `update.effective_chat.id == int(TELEGRAM_CHAT_ID)` (or an allowlist) and silently drop otherwise.
- Prefer a `filters.Chat(chat_id=...)` filter on each `CommandHandler`.

### Confidence
High

### Exploitability
Medium (requires knowing/guessing the bot handle)

---

## AOS-006 — No rate limiting, brute-force, or DoS protection

### Severity
High

### CWE Category
CWE-770: Allocation of Resources Without Limits or Throttling

### OWASP Category
A04:2021 — Insecure Design

### Location
`backend/main.py` (all endpoints); no throttling middleware anywhere.

### Vulnerability Description
There is no rate limiting, request quota, account lockout, or throttling on any endpoint. Write endpoints (`POST /api/attempts`, `POST /api/sessions`) insert rows unbounded; read endpoints (`/api/dashboard`, `/api/weaknesses`) run many sub-queries per call (the dashboard issues per-priority N+1 queries, and `_update_mastery` runs `LIKE '%' || ? || '%'` full scans). An attacker can trivially exhaust CPU, disk (DB growth), and SQLite write locks (WAL).

### Attack Scenario
Attacker loops `POST /api/attempts` thousands of times per second: unbounded DB growth, mastery corruption, and SQLite write contention that stalls legitimate requests (DoS).

### Impact
Availability loss; disk exhaustion; data pollution; cost amplification.

### Evidence
- `_todays_priorities()` issues a fresh `_query` per priority row (N+1).
- No `slowapi`/`limits`/gateway throttle present in `requirements.txt` or code.

### Reproduction Steps
1. `while true; do curl -s -X POST .../api/attempts -d '{...}' -H 'Content-Type: application/json'; done` — rows accumulate without bound.

### Recommended Fix
- Add per-IP/per-principal rate limiting (e.g. `slowapi`, or gateway/WAF rules).
- Cap request body sizes; add global concurrency limits; throttle write endpoints aggressively.

### Confidence
High

### Exploitability
High

---

## AOS-007 — Unbounded `limit` parameter / query amplification

### Severity
Medium

### CWE Category
CWE-770: Allocation of Resources Without Limits or Throttling

### OWASP Category
A04:2021 — Insecure Design

### Location
`backend/main.py:124` `get_papers(subject, limit: int = 500)`; the `limit` query parameter is an unbounded `int` with no upper cap.

### Vulnerability Description
`GET /api/papers?limit=99999999` is accepted verbatim and passed to `LIMIT ?`. There is no maximum. Combined with the grouped join over papers/questions/attempts, large `limit` values plus repeated calls amplify memory/CPU.

### Attack Scenario
Attacker requests `/api/papers?limit=2000000000` repeatedly to force large result materialization and JSON serialization.

### Impact
Memory pressure and response-time degradation; contributes to DoS.

### Evidence
```python
def get_papers(subject: str | None = None, limit: int = 500) -> list[dict]:
    ... f"... LIMIT ?", tuple(params) + (limit,))
```

### Reproduction Steps
1. `curl 'http://<host>:8000/api/papers?limit=100000000'`.

### Recommended Fix
- Use `limit: int = Query(500, ge=1, le=500)` to clamp the value; reject or cap oversized requests.

### Confidence
High

### Exploitability
Medium

---

## AOS-008 — Missing security headers (CSP, X-Frame-Options, HSTS, nosniff)

### Severity
Medium

### CWE Category
CWE-693: Protection Mechanism Failure; CWE-1021: Improper Restriction of Rendered UI Layers (clickjacking)

### OWASP Category
A05:2021 — Security Misconfiguration

### Location
`frontend/next.config.mjs` (empty config — no `headers()`); `backend/main.py` (no header middleware).

### Vulnerability Description
Neither the Next.js frontend nor the FastAPI backend sets security response headers. There is no Content-Security-Policy, no `X-Frame-Options`/`frame-ancestors` (clickjacking), no `Strict-Transport-Security`, no `X-Content-Type-Options: nosniff`, and no `Referrer-Policy`. `next.config.mjs` is an empty object.

### Attack Scenario
- Clickjacking: attacker embeds the app in an iframe and overlays UI to trick the user into actions.
- MIME sniffing / weak CSP increases the blast radius of any future injection.

### Impact
Increased exposure to clickjacking, content-sniffing, and downgrade attacks; no defense-in-depth against XSS.

### Evidence
```js
// frontend/next.config.mjs
const nextConfig = {};
export default nextConfig;
```

### Reproduction Steps
1. Load the deployed site inside `<iframe src="https://app/...">` — it renders (no `frame-ancestors`/`X-Frame-Options`).

### Recommended Fix
- Add a `headers()` block in `next.config.mjs` setting CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and HSTS.
- Add equivalent headers (e.g. `secure.py` or middleware) to the FastAPI responses.

### Confidence
High

### Exploitability
Medium

---

## AOS-009 — Third-party CDN stylesheet loaded `@latest` without Subresource Integrity

### Severity
Medium

### CWE Category
CWE-829: Inclusion of Functionality from Untrusted Control Sphere

### OWASP Category
A08:2021 — Software and Data Integrity Failures

### Location
`frontend/app/layout.tsx` — `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css">`

### Vulnerability Description
The root layout pulls a stylesheet from a public CDN pinned to the floating `@latest` tag with **no Subresource Integrity (`integrity`) hash** and no version pin. Whatever the CDN serves at request time is trusted implicitly. A compromised/poisoned CDN package version (a real supply-chain vector) would be loaded into every page.

### Attack Scenario
If the `@tabler/icons-webfont` package or the jsDelivr cache is compromised, malicious CSS (e.g. exfiltration via `background:url()` on attribute selectors, or UI redressing) executes for all users. `@latest` guarantees you receive the malicious version automatically.

### Impact
Supply-chain compromise of the frontend; potential data exfiltration / UI manipulation.

### Evidence
```html
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@latest/dist/tabler-icons.min.css" />
```
Note the app also already depends on `@tabler/icons-react` in `package.json`, so the external CDN font is redundant.

### Recommended Fix
- Pin an exact version and add an `integrity` SRI hash + `crossorigin="anonymous"`, **or** self-host the asset / use the already-installed `@tabler/icons-react`. Restrict allowed sources via CSP (`style-src`).

### Confidence
High

### Exploitability
Low (depends on CDN/package compromise)

---

## AOS-010 — No transport security (plaintext HTTP API)

### Severity
Medium

### CWE Category
CWE-319: Cleartext Transmission of Sensitive Information

### OWASP Category
A02:2021 — Cryptographic Failures

### Location
`frontend/lib/api.ts:15` (`BASE_URL = ... ?? "http://localhost:8000"`); `start-backend.sh` (plain Uvicorn, no TLS).

### Vulnerability Description
The API is served over plain HTTP and the frontend default base URL is `http://`. No HTTPS/TLS is configured or enforced. Academic data and free-text notes traverse the network in cleartext.

### Attack Scenario
On a shared/hostile network, an on-path attacker reads or tampers with API traffic (responses and `POST /api/attempts` bodies).

### Impact
Confidentiality and integrity of all API traffic; enables session/credential capture once auth is added.

### Evidence
```ts
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
```

### Recommended Fix
- Serve the API only over HTTPS behind a TLS-terminating proxy; force the frontend base URL to `https://`; enable HSTS (see AOS-008).

### Confidence
High

### Exploitability
Medium

---

## AOS-011 — Unvalidated `answer_image_path` stored from client (path injection / stored traversal)

### Severity
Medium

### CWE Category
CWE-22: Improper Limitation of a Pathname to a Restricted Directory

### OWASP Category
A03:2021 — Injection / A04:2021 — Insecure Design

### Location
`backend/main.py:828` (`AttemptCreate.answer_image_path: str | None`) → inserted at line 904-911 without validation.

### Vulnerability Description
The client supplies an arbitrary filesystem path string (`answer_image_path`) that is persisted verbatim into `attempts`. There is no validation, canonicalization, or allowlisting. Although no current endpoint serves this path back as a file, storing an attacker-controlled absolute/`../` path is a latent stored path-traversal: the moment any feature reads or serves `answer_image_path` (image preview, diagram serving), it becomes an arbitrary-file-read/SSRF-style primitive.

### Attack Scenario
Attacker submits `{"answer_image_path": "/etc/passwd"}` (or `../../secret.db`). When a future image-serving endpoint dereferences it, it reads arbitrary host files.

### Impact
Latent arbitrary file disclosure; data-integrity pollution of stored paths.

### Evidence
```python
class AttemptCreate(BaseModel):
    ...
    answer_image_path: str | None = None   # accepted as-is
...
conn.execute("INSERT INTO attempts (..., answer_image_path, ...) VALUES (..., ?, ...)",
             (..., body.answer_image_path, ...))
```

### Reproduction Steps
1. `POST /api/attempts` with `"answer_image_path":"../../../../etc/passwd"` → stored verbatim.

### Recommended Fix
- Do not accept raw filesystem paths from clients. Accept an uploaded file or an opaque ID; generate the storage path server-side under a fixed directory; validate with `Path.resolve()` and confirm it is within an allowed base (`is_relative_to`).

### Confidence
Medium

### Exploitability
Low (no current sink) — Medium if image serving is added

---

## AOS-012 — Business-logic / data-integrity gaps (cross-paper, negative values)

### Severity
Medium

### CWE Category
CWE-840: Business Logic Errors

### OWASP Category
A04:2021 — Insecure Design

### Location
`backend/main.py`: `log_question_time` (781), `create_attempt` (884), `create_session` (758).

### Vulnerability Description
Several relational/business invariants are unenforced:
- `log_question_time` accepts any `question_id` for a session without checking the question belongs to the session's paper.
- `create_attempt` accepts `session_id` and `question_id` independently with no check that the question belongs to that session's paper.
- `SessionCreate.official_time_seconds`/`target_time_seconds` have no `ge=0` bound (negative values accepted), and `SessionComplete.total_time_seconds` is unvalidated — feeding skewed analytics/grade math (`_grade_from_mastery`, score trend).

### Attack Scenario
A client logs attempts for unrelated questions under a session, or submits negative times, silently corrupting analytics, mastery, and predicted grades — undermining the platform's core "Data Integrity" governing principle.

### Impact
Integrity of analytics and the learning model; non-malicious clients can also corrupt data through these gaps.

### Evidence
```python
class SessionCreate(BaseModel):
    paper_id: int
    official_time_seconds: int = 0   # no ge=0
    target_time_seconds: int = 0     # no ge=0
```

### Recommended Fix
- Validate that `question_id` belongs to the session's paper before writing.
- Add `Field(ge=0)` bounds to all time fields; reject inconsistent records.

### Confidence
High

### Exploitability
Medium

---

## AOS-013 — Error / exception detail leakage to clients and logs

### Severity
Low

### CWE Category
CWE-209: Generation of Error Message Containing Sensitive Information

### OWASP Category
A05:2021 — Security Misconfiguration

### Location
`agents/delivery/telegram_agent.py:197` (`f"• *{subject}*: Error — {exc}"`); `frontend/lib/api.ts:23-26` (echoes server error body); `backend/main.py` HTTPException details echo IDs.

### Vulnerability Description
Raw exception text is surfaced to users (Telegram reply includes `{exc}`), and the frontend logs/propagates the full server error body. While SQLite errors are caught and only logged in `_query`, the Telegram path and the frontend can reveal internal details (stack-relevant messages, schema hints).

### Attack Scenario
An attacker probes inputs to elicit exception strings that reveal internal structure (table/column names, file paths), aiding further attacks.

### Impact
Information disclosure aiding reconnaissance.

### Evidence
```python
except Exception as exc:
    lines.append(f"• *{subject}*: Error — {exc}")
```

### Recommended Fix
- Return generic error messages to clients; log details server-side only. Never interpolate raw exception text into user-facing responses.

### Confidence
High

### Exploitability
Low

---

## AOS-014 — CORS configuration hardcoded to localhost (and likely to be loosened insecurely)

### Severity
Low

### CWE Category
CWE-942: Permissive Cross-domain Policy with Untrusted Domains

### OWASP Category
A05:2021 — Security Misconfiguration

### Location
`backend/main.py:38-44`

### Vulnerability Description
CORS `allow_origins` is hardcoded to `http://localhost:3000/3001`. In production (Vercel frontend, AOS deploy config in `vercel.json`), this breaks cross-origin calls, creating strong pressure for a developer to "fix" it by setting `allow_origins=["*"]`. With the current `allow_credentials=False` that is less catastrophic, but if credentials/auth are added later (AOS-001 fix) a wildcard becomes dangerous. The configuration is not environment-driven, inviting an insecure quick fix.

### Attack Scenario
A developer sets `allow_origins=["*"]` to unblock production; once cookie/token auth exists, any site can issue authenticated cross-origin requests.

### Impact
Future cross-origin data theft if loosened together with credentialed auth.

### Evidence
```python
allow_origins=["http://localhost:3000", "http://localhost:3001"],
allow_credentials=False,
```

### Recommended Fix
- Drive allowed origins from an environment variable (explicit production origin list); never combine `allow_origins=["*"]` with credentials. Document this constraint.

### Confidence
Medium

### Exploitability
Low

---

## AOS-015 — Dependency currency / supply-chain monitoring gap

### Severity
Low

### CWE Category
CWE-1104: Use of Unmaintained Third-Party Components / CWE-1395: Dependency on Vulnerable Third-Party Component

### OWASP Category
A06:2021 — Vulnerable and Outdated Components

### Location
`requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`.

### Vulnerability Description
Dependencies are pinned with floating lower bounds (`>=`) in `requirements.txt`, so builds are not reproducible and may silently pull future vulnerable releases. The frontend uses `next@14.2.35` (a fast-moving line with a history of advisories — middleware/SSRF/cache CVEs in the 14.2.x series); it is reasonably current but must be tracked. No automated dependency scanning (Dependabot/`pip-audit`/`npm audit`) or lockfile for Python is present. No CI security workflow exists in the repo.

### Attack Scenario
A transitive dependency CVE (e.g. in `pix2tex`, `pdf2image`/poppler, `pdfplumber`, or a future Next.js advisory) ships into production unnoticed because nothing scans or pins.

### Impact
Exposure to known-vulnerable components; non-reproducible builds.

### Evidence
```
fastapi[standard]>=0.115.0
pix2tex>=0.1.2
python-telegram-bot>=21.0
```
```json
"next": "14.2.35"
```

### Recommended Fix
- Pin exact versions and add a Python lockfile (`uv.lock`/`pip-compile`); enable Dependabot and run `pip-audit` + `npm audit` in CI; subscribe to Next.js security advisories and patch promptly.

### Confidence
Medium

### Exploitability
Low

---

## AOS-016 — Hardcoded developer absolute path in launch script

### Severity
Low

### CWE Category
CWE-1188: Insecure Default Initialization / CWE-200 (information exposure)

### OWASP Category
A05:2021 — Security Misconfiguration

### Location
`start-backend.sh:14` — fallback `VENV_PYTHON="/Users/mouadmaamma/academic-os/.venv/bin/uvicorn"`.

### Vulnerability Description
The script hardcodes a developer's home directory path as a fallback interpreter location. This leaks the developer's username and local layout, and makes the production launch path fragile/non-portable (could resolve to an unexpected binary on a different host).

### Attack Scenario
Minor reconnaissance (username disclosure); operational fragility if the fallback resolves unexpectedly.

### Impact
Information leak; deployment reliability.

### Evidence
```bash
VENV_PYTHON="/Users/mouadmaamma/academic-os/.venv/bin/uvicorn"
```

### Recommended Fix
- Resolve the interpreter from the active virtualenv / `$VIRTUAL_ENV` or require it be passed in; remove the hardcoded personal path.

### Confidence
High

### Exploitability
Low

---

## AOS-017 — Sensitive identifiers written to logs / stdout

### Severity
Informational

### CWE Category
CWE-532: Insertion of Sensitive Information into Log File

### OWASP Category
A09:2021 — Security Logging and Monitoring Failures

### Location
`scripts/send_briefing.py:44` (prints `TELEGRAM_CHAT_ID`); general logging configuration.

### Vulnerability Description
`send_briefing.py` prints the Telegram chat ID to stdout on success. More broadly, there is no security logging/monitoring strategy (no audit log of writes, no alerting). The chat ID is a low-sensitivity identifier, but combined with logs aggregation it is needless exposure, and the absence of audit logging means the anonymous writes (AOS-001/002) would go undetected.

### Attack Scenario
Log scraping reveals the delivery chat ID; lack of audit logging means data tampering leaves no trail.

### Impact
Minor identifier exposure; no detection capability for abuse.

### Evidence
```python
print(f"Sent daily briefing ({len(text)} chars) to chat {TELEGRAM_CHAT_ID}.")
```

### Recommended Fix
- Avoid printing identifiers; introduce structured audit logging for all write operations once auth exists; add monitoring/alerting.

### Confidence
High

### Exploitability
Low

---

## Areas Reviewed With No Vulnerability Found (Negative Results)

These were specifically checked and found **clean**, which is worth recording:

- **SQL Injection (CWE-89):** All database access in `backend/main.py` and `agents/*.py` uses parameterized queries (`?` placeholders). The dynamic `f"""..."""` SQL strings only interpolate **statically-built** `WHERE` fragments and `?`-placeholder lists (`",".join("?" * len(ids))`); no user data is concatenated into SQL. `IN (...)` clauses are built from placeholder counts, not values. **No SQL injection found.**
- **Cross-Site Scripting (CWE-79):** No `dangerouslySetInnerHTML`, `innerHTML`, `eval`, or raw HTML injection in the React frontend (`frontend/`). DB-sourced text (`question_text`, `notes`) is rendered as React children (auto-escaped).
- **Command Injection (CWE-78):** No `os.system`, `subprocess`, `shell=True`, `eval`, or `exec` calls anywhere in the codebase. OCR (`ingestion/ocr.py`) calls library APIs (`pytesseract`, `pdf2image`), not shell commands.
- **Insecure Deserialization (CWE-502):** No `pickle`, `yaml.load`, or `marshal` usage.
- **Secrets in VCS:** No `.db`, `.env`, `.pem`, or credential files are tracked by git; `.gitignore` correctly excludes `.env`, `*.db`, and `data/`. `.env.example` files contain only placeholders. **No hardcoded secrets found in source.**

These negative results should be re-verified whenever new endpoints, templates, or shell-invoking code are added.

---

## Prioritized Remediation Roadmap

1. **Do not deploy to the public internet until AOS-001/002/003 are fixed.** Add authentication + per-resource authorization, and stop binding `0.0.0.0` without an authenticating proxy. These three are the entire ballgame.
2. Gate the Telegram bot by chat ID (AOS-005).
3. Add rate limiting and clamp `limit` (AOS-006, AOS-007).
4. Add security headers + HTTPS/HSTS (AOS-008, AOS-010).
5. Pin/SRI the CDN asset or self-host (AOS-009); validate `answer_image_path` (AOS-011); enforce relational invariants (AOS-012).
6. Tighten error handling, CORS-via-env, dependency scanning, and audit logging (AOS-013–017).
