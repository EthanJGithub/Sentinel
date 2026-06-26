import type { PlanRequest, PlanResult, TraceEvent } from "./types";

const AGENT_URL = (import.meta as any).env?.VITE_AGENT_URL ?? "http://localhost:8000";

export async function health(): Promise<any> {
  const r = await fetch(`${AGENT_URL}/health`);
  return r.json();
}

export async function approve(planId: string): Promise<any> {
  const r = await fetch(`${AGENT_URL}/approve/${planId}`, { method: "POST" });
  return r.json();
}

/** Stream the live agent trace over WebSocket; resolves with the final PlanResult.
 *  Falls back to the REST /plan endpoint if the socket cannot connect. */
export function runPlanStreaming(
  req: PlanRequest,
  onTrace: (ev: TraceEvent) => void,
): Promise<PlanResult> {
  return new Promise((resolve, reject) => {
    const wsUrl = AGENT_URL.replace(/^http/, "ws") + "/ws/plan";
    let settled = false;
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
    } catch {
      return restFallback(req).then(resolve, reject);
    }
    const failTimer = setTimeout(() => {
      if (!settled) { try { ws.close(); } catch {} restFallback(req).then(resolve, reject); settled = true; }
    }, 4000);

    ws.onopen = () => { clearTimeout(failTimer); ws.send(JSON.stringify(req)); };
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "trace") onTrace(msg.event as TraceEvent);
      else if (msg.type === "result") { settled = true; resolve(msg.result as PlanResult); ws.close(); }
      else if (msg.type === "error") { settled = true; reject(new Error(msg.error)); ws.close(); }
    };
    ws.onerror = () => {
      if (!settled) { clearTimeout(failTimer); settled = true; restFallback(req).then(resolve, reject); }
    };
  });
}

async function restFallback(req: PlanRequest): Promise<PlanResult> {
  const r = await fetch(`${AGENT_URL}/plan`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(req),
  });
  if (!r.ok) throw new Error(`agent error ${r.status}`);
  return r.json();
}
