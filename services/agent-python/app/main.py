"""FastAPI app — the orchestration surface the React console talks to.
REST for auth/plan/approve/report; WebSocket streams the live agent trace.

Auth: JWT bearer + RBAC (operator < approver < admin). /plan needs operator+,
/approve needs approver+ (the regulated HITL gate). Plus security headers, a
simple per-IP rate limiter, and configurable CORS.
"""
from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from .auth import (User, create_token, current_user, get_user_store,
                   require_role, user_from_ws_token)
from .config import get_settings
from .observability import METRICS, get_exporter, log_event
from .persistence import get_store
from .runner import RUNS, approve_plan, get_run, run_plan
from .schema import LoginRequest, PlanRequest, TokenResponse

settings = get_settings()
app = FastAPI(title="Sentinel — Agent Orchestration", version="0.3.0")


@app.on_event("startup")
def _startup():
    problems = settings.validate_secrets()
    if problems:
        # fail fast in production posture (REQUIRE_STRONG_SECRETS=true)
        raise RuntimeError("insecure configuration: " + "; ".join(problems))
    log_event("startup", persistence="postgres" if get_store().enabled else "in-memory",
              langfuse=get_exporter().enabled, real_models=settings.has_anthropic,
              require_strong_secrets=settings.require_strong_secrets)

origins = ["*"] if settings.cors_origins.strip() == "*" else [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"],
                   allow_headers=["*"], allow_credentials=False)


# ---------------------------------------------------------------------------
# security headers + simple per-IP rate limiter
# ---------------------------------------------------------------------------
_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def guard(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = _hits[ip]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.rate_limit_per_min and request.url.path not in ("/health", "/ready", "/metrics"):
        return JSONResponse({"error": "rate limit exceeded"}, status_code=429)
    window.append(now)

    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["X-XSS-Protection"] = "1; mode=block"
    return resp


# ---------------------------------------------------------------------------
# public
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "agent-python", "provider_mode": settings.provider_mode,
            "real_models": settings.has_anthropic, "catalog": "remote" if settings.catalog_url else "local-json",
            "rag": "pgvector" if (settings.database_url and settings.has_openai) else "local-keyword",
            "persistence": "postgres" if get_store().enabled else "in-memory",
            "auth": "jwt+rbac", "multi_tenant": True,
            "observability": {"metrics": "/metrics", "langfuse": get_exporter().enabled}}


@app.get("/ready")
def ready():
    # readiness distinct from liveness: DB reachable if configured
    ok = (not settings.database_url) or get_store().enabled
    return JSONResponse({"ready": ok}, status_code=200 if ok else 503)


@app.get("/metrics")
def metrics():
    # Prometheus scrape target (public by convention; no PHI in metrics)
    return PlainTextResponse(METRICS.prometheus(), media_type="text/plain; version=0.0.4")


@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = get_user_store().authenticate(req.email, req.password)
    if not user:
        return JSONResponse({"error": "invalid credentials"}, status_code=401)
    return TokenResponse(access_token=create_token(user), expires_in=settings.jwt_ttl_seconds,
                         user=user.public())


# ---------------------------------------------------------------------------
# authenticated
# ---------------------------------------------------------------------------
@app.get("/auth/me")
def me(user: User = Depends(current_user)):
    return user.public()


def _scope(user: User):
    """tenant scope for reads: None = cross-tenant (admin), else the user's tenant."""
    return None if user.cross_tenant else user.tenant_id


@app.post("/plan")
async def plan(req: PlanRequest, user: User = Depends(require_role("operator"))):
    result = await asyncio.to_thread(run_plan, req, None, user.email, user.tenant_id)
    return json.loads(result.model_dump_json())


@app.post("/approve/{plan_id}")
def approve(plan_id: str, request: Request, user: User = Depends(require_role("approver"))):
    # RBAC: only an approver/admin may commit an order (the regulated HITL gate).
    # Forward the approver's bearer so the C# system-of-record authorizes it too.
    auth = request.headers.get("authorization", "")
    bearer = auth[7:] if auth.lower().startswith("bearer ") else None
    return approve_plan(plan_id, user.email, _scope(user), bearer, user.facility)


@app.get("/runs/{plan_id}")
def get_run_ep(plan_id: str, user: User = Depends(current_user)):
    res = get_run(plan_id, _scope(user))
    return json.loads(res.model_dump_json()) if res else JSONResponse({"error": "unknown plan_id"}, status_code=404)


@app.get("/runs")
def list_runs(user: User = Depends(current_user)):
    store = get_store()
    if store.enabled:
        return store.list_runs(_scope(user))
    scope = _scope(user)
    return [{"plan_id": p, "tenant_id": r.metrics.get("tenant_id", "cedarwood"), "status": r.status,
             "violations": r.violations, "abstentions": r.abstentions, "cost_usd": r.metrics.get("total_cost_usd")}
            for p, r in RUNS.items()
            if scope is None or r.metrics.get("tenant_id", "cedarwood") == scope]


# ---------------------------------------------------------------------------
# live trace over WebSocket (token in query ?token= or first message)
# ---------------------------------------------------------------------------
@app.websocket("/ws/plan")
async def ws_plan(ws: WebSocket):
    await ws.accept()
    try:
        token = ws.query_params.get("token")
        payload = await ws.receive_json()
        token = token or payload.pop("token", None)
        try:
            user = user_from_ws_token(token)
        except Exception:
            await ws.send_json({"type": "error", "error": "unauthorized"})
            await ws.close(code=4401)
            return

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_event(ev):
            loop.call_soon_threadsafe(queue.put_nowait, ev.model_dump())

        async def drain():
            while True:
                ev = await queue.get()
                if ev is None:
                    break
                await ws.send_json({"type": "trace", "event": ev})

        drain_task = asyncio.create_task(drain())
        req = PlanRequest(**payload)
        result = await asyncio.to_thread(run_plan, req, on_event, user.email, user.tenant_id)
        await queue.put(None)
        await drain_task
        await ws.send_json({"type": "result", "result": json.loads(result.model_dump_json())})
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        await ws.send_json({"type": "error", "error": str(e)})
    finally:
        await ws.close()
