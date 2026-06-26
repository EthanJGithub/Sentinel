"""Clients for the C# catalog service and the TS MCP server. Both degrade to an
in-process implementation backed by the committed seed JSON so the agent graph runs
with no peer services up (offline demo + eval)."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

import httpx

from .config import Settings


# ---------------------------------------------------------------------------
# Catalog client (C# system of record, or JSON fallback)
# ---------------------------------------------------------------------------
class CatalogClient:
    def __init__(self, settings: Settings):
        self.s = settings
        self.base = settings.catalog_url.rstrip("/") if settings.catalog_url else ""
        self._local = None if self.base else _LocalCatalog(settings)

    def _get(self, path: str, **params) -> Any:
        with httpx.Client(timeout=20) as c:
            r = c.get(f"{self.base}{path}", params=params)
            r.raise_for_status()
            return r.json()

    def search(self, *, category: str, room: Optional[str] = None, limit: int = 50) -> list[dict]:
        if self._local:
            return self._local.search(category=category, room=room, limit=limit)
        return self._get("/api/catalog/search", category=category, room=room or "", limit=limit)

    def price(self, skus: list[str], contract_id: Optional[str]) -> list[dict]:
        if self._local:
            return self._local.price(skus, contract_id)
        with httpx.Client(timeout=20) as c:
            r = c.post(f"{self.base}/api/contract/price", json={"skus": skus, "contractId": contract_id})
            r.raise_for_status()
            return r.json()

    def get(self, sku: str) -> Optional[dict]:
        if self._local:
            return self._local.get(sku)
        try:
            return self._get(f"/api/catalog/{sku}")
        except httpx.HTTPStatusError:
            return None

    def substitutions(self, sku: str, limit: int = 5) -> list[dict]:
        if self._local:
            return self._local.substitutions(sku, limit)
        return self._get(f"/api/catalog/{sku}/substitutions", limit=limit)

    def place_order(self, plan_id: str, facility: str, lines: list[dict]) -> dict:
        if self._local:
            return self._local.place_order(plan_id, facility, lines)
        with httpx.Client(timeout=20) as c:
            r = c.post(f"{self.base}/api/orders",
                       json={"planId": plan_id, "facilityName": facility, "lines": lines})
            r.raise_for_status()
            return r.json()


class _LocalCatalog:
    """In-process mirror of the C# service backed by data/catalog/*.json."""

    def __init__(self, settings: Settings):
        self.products = {p["sku"]: p for p in json.loads(settings.catalog_json.read_text("utf-8"))}
        c = json.loads(settings.contracts_json.read_text("utf-8"))
        self.prices: dict[str, list[dict]] = {}
        for cp in c["contract_prices"]:
            self.prices.setdefault(cp["sku"], []).append(cp)

    def _best(self, sku: str, contract_id: Optional[str]) -> tuple[float, Optional[str]]:
        pool = self.prices.get(sku, [])
        if contract_id:
            pool = [p for p in pool if p["contract_id"] == contract_id] or self.prices.get(sku, [])
        if not pool:
            return self.products[sku]["list_price"], None
        best = min(pool, key=lambda p: p["price"])
        return best["price"], best["contract_id"]

    def _dto(self, p: dict, contract_id: Optional[str] = None) -> dict:
        bp, cid = self._best(p["sku"], contract_id)
        return {**p, "bestPrice": bp, "bestContractId": cid,
                "applicableRooms": p.get("applicable_rooms", []), "listPrice": p["list_price"]}

    def search(self, *, category: str, room: Optional[str], limit: int) -> list[dict]:
        out = [self._dto(p) for p in self.products.values() if p["category"] == category
               and (not room or room in p.get("applicable_rooms", []))]
        return out[:limit]

    def price(self, skus: list[str], contract_id: Optional[str]) -> list[dict]:
        res = []
        for sku in skus:
            p = self.products.get(sku)
            if not p:
                continue
            bp, cid = self._best(sku, contract_id)
            lp = p["list_price"]
            res.append({"sku": sku, "listPrice": lp, "bestPrice": bp, "contractId": cid,
                        "savingsPct": round((lp - bp) / lp * 100, 1) if lp else 0})
        return res

    def get(self, sku: str) -> Optional[dict]:
        p = self.products.get(sku)
        return self._dto(p) if p else None

    def substitutions(self, sku: str, limit: int) -> list[dict]:
        orig = self.products.get(sku)
        if not orig:
            return []
        subs = [self._dto(p) for p in self.products.values()
                if p["category"] == orig["category"] and p["sku"] != sku and p.get("compliant", True)]
        subs.sort(key=lambda d: d["bestPrice"])
        return subs[:limit]

    def place_order(self, plan_id: str, facility: str, lines: list[dict]) -> dict:
        import uuid
        total = 0.0
        for l in lines:
            bp, _ = self._best(l["sku"], l.get("contractId"))
            total += bp * l["qty"]
        return {"id": str(uuid.uuid4()), "status": "PLACED", "total": round(total, 2),
                "lineCount": len(lines), "note": "local-fallback (C# service not connected)"}


@lru_cache
def get_catalog_client_cached(_key: str) -> CatalogClient:  # pragma: no cover
    raise NotImplementedError
