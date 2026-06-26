"""FastAPI app — the orchestration surface the React console talks to.
REST for plan/approve/report; WebSocket streams the live agent trace."""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .runner import RUNS, approve_plan, run_plan
from .schema import PlanRequest

app = FastAPI(title="Sentinel — Agent Orchestration", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    s = get_settings()
    return {"status": "ok", "service": "agent-python", "provider_mode": s.provider_mode,
            "real_models": s.has_anthropic, "catalog": "remote" if s.catalog_url else "local-json",
            "rag": "pgvector" if (s.database_url and s.has_openai) else "local-keyword"}


@app.post("/plan")
async def plan(req: PlanRequest):
    # run the (sync) graph in a worker thread so the event loop stays free
    result = await asyncio.to_thread(run_plan, req)
    return json.loads(result.model_dump_json())


@app.post("/approve/{plan_id}")
def approve(plan_id: str):
    return approve_plan(plan_id)


@app.get("/runs/{plan_id}")
def get_run(plan_id: str):
    res = RUNS.get(plan_id)
    return json.loads(res.model_dump_json()) if res else {"error": "unknown plan_id"}


@app.get("/runs")
def list_runs():
    return [{"plan_id": p, "status": r.status, "violations": r.violations,
             "abstentions": r.abstentions, "cost": r.metrics.get("total_cost_usd")}
            for p, r in RUNS.items()]


@app.websocket("/ws/plan")
async def ws_plan(ws: WebSocket):
    """Stream the live trace as the graph executes (nodes light up in the console)."""
    await ws.accept()
    try:
        payload = await ws.receive_json()
        req = PlanRequest(**payload)
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
        result = await asyncio.to_thread(run_plan, req, on_event)
        await queue.put(None)
        await drain_task
        await ws.send_json({"type": "result", "result": json.loads(result.model_dump_json())})
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        await ws.send_json({"type": "error", "error": str(e)})
    finally:
        await ws.close()
