"""Cross-service integration test against a running stack (agent + C# catalog + MCP +
Postgres). Skipped in unit CI; runs when SENTINEL_E2E_URL is set (e.g. against the
docker-compose stack):

    SENTINEL_E2E_URL=http://localhost:8000 pytest tests/test_integration.py
"""
import json
import os
import urllib.request

import pytest

URL = os.getenv("SENTINEL_E2E_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set SENTINEL_E2E_URL to run integration tests")


def _call(path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data,
                                 method="POST" if data is not None else "GET")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, None


def _login(email, pw):
    _, d = _call("/auth/login", {"email": email, "password": pw})
    return d["access_token"]


def test_rbac_and_tenant_isolation_end_to_end():
    op = _login("operator@cedarwood.health", "Operator!2026")
    ap = _login("approver@cedarwood.health", "Approver!2026")
    mt = _login("operator@maplewood.health", "Maple!2026")

    # operator can plan but not approve
    st, plan = _call("/plan", {"request": "Equip a 12-bed wing", "budget_usd": 200000,
                               "plant_violation_sku": "TRAP-NC-001"}, op)
    assert st == 200 and plan["violations"] == 1
    assert _call(f"/approve/{plan['plan_id']}", {}, op)[0] == 403   # RBAC

    # approver places the order through the C# system-of-record
    st_a, appr = _call(f"/approve/{plan['plan_id']}", {}, ap)
    assert st_a == 200 and appr["status"] == "ORDERED"

    # tenant isolation: maplewood cannot read cedarwood's run
    assert _call(f"/runs/{plan['plan_id']}", token=mt)[0] == 404


def test_metrics_and_ready():
    assert _call("/ready")[0] == 200
    import urllib.request
    body = urllib.request.urlopen(URL + "/metrics", timeout=10).read().decode()
    assert "sentinel_plans_total" in body
