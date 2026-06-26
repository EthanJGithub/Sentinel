"""Multi-tenancy + observability tests."""
from app.auth import User, create_token, decode_token
from app.observability import METRICS
from app.runner import get_run, run_plan
from app.schema import PlanRequest


def test_token_carries_tenant():
    u = User(email="o@maplewood.health", name="M", role="operator", tenant_id="maplewood")
    assert decode_token(create_token(u))["tenant_id"] == "maplewood"


def test_admin_is_cross_tenant():
    assert User(email="a", name="A", role="admin", tenant_id="*").cross_tenant
    assert not User(email="o", name="O", role="operator", tenant_id="cedarwood").cross_tenant


def test_run_is_tenant_scoped():
    res = run_plan(PlanRequest(request="Equip a 12-bed wing", budget_usd=200000),
                   tenant_id="maplewood")
    # same tenant can read it; a different tenant cannot
    assert get_run(res.plan_id, "maplewood") is not None
    assert get_run(res.plan_id, "cedarwood") is None
    # cross-tenant (admin / None) can read it
    assert get_run(res.plan_id, None) is not None


def test_metrics_increment():
    before = METRICS.plans_total
    run_plan(PlanRequest(request="Equip a 12-bed wing", budget_usd=200000), tenant_id="cedarwood")
    assert METRICS.plans_total == before + 1
    assert "sentinel_plans_total" in METRICS.prometheus()
