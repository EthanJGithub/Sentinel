"""Shared services injected into every graph node (kept out of the serializable
graph state)."""
from __future__ import annotations

from dataclasses import dataclass

from ..clients import CatalogClient, MCPClient
from ..compliance import Rule, load_rules
from ..config import Settings
from ..monitoring import CostMeter
from ..providers import ModelRouter
from ..rag import build_retriever


@dataclass
class AgentContext:
    settings: Settings
    router: ModelRouter
    retriever: object
    catalog: CatalogClient
    mcp: MCPClient
    rules: list[Rule]
    meter: CostMeter

    @classmethod
    def build(cls, settings: Settings, meter: CostMeter) -> "AgentContext":
        return cls(
            settings=settings,
            router=ModelRouter(settings),
            retriever=build_retriever(settings),
            catalog=CatalogClient(settings),
            mcp=MCPClient(settings),
            rules=load_rules(settings),
            meter=meter,
        )
