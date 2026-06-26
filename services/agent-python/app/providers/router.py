"""Cost-aware model router. Maps each agent capability to the cheapest adequate
model: Haiku for routing/extraction, Opus for compliance reasoning, OpenAI for an
independent structured cross-check. Falls back to deterministic heuristics when no
keys are present (PROVIDER_MODE=dev or missing keys) so dev/eval cost $0.

Every capability returns (result, model_id, tokens_in, tokens_out) so the CostMeter
can attribute spend per node and per model."""
from __future__ import annotations

import json
import re
from typing import Optional

from ..config import Settings
from .base import LLMResponse, approx_tokens
from .vendors import AnthropicProvider, HeuristicProvider, OpenAIProvider


class ModelRouter:
    def __init__(self, settings: Settings):
        self.s = settings
        self.heuristic = HeuristicProvider()
        self.anthropic: Optional[AnthropicProvider] = None
        self.openai: Optional[OpenAIProvider] = None
        if settings.has_anthropic:
            try:
                self.anthropic = AnthropicProvider(settings.anthropic_api_key)
            except Exception:
                self.anthropic = None
        if settings.has_openai:
            try:
                self.openai = OpenAIProvider(settings.openai_api_key)
            except Exception:
                self.openai = None

    # -- which provider/model handles "reasoning" (compliance) --
    @property
    def using_real_models(self) -> bool:
        return self.anthropic is not None

    def active_models(self) -> dict:
        return {
            "route": self.s.model_route if self.anthropic else "heuristic-local",
            "reason": self.s.model_reason if self.anthropic else "heuristic-local",
            "cross_check": "gpt-4o-mini" if self.openai else "heuristic-local",
            "embed": self.s.model_embed if self.openai else "local-keyword-rag",
        }

    # ------------------------------------------------------------------
    # CAPABILITY 1 — Planner: NL request -> structured procurement spec (cheap/Haiku)
    # ------------------------------------------------------------------
    def plan_spec(self, request: str, care_type: str, budget: float):
        if self.anthropic:
            system = ("You are a senior-care procurement planner. Decompose the request into a JSON "
                      "procurement spec with keys: summary (str), rooms (list of {room_type, count, "
                      "categories[]}), constraints (list[str]). room_type in "
                      "[resident_room,bathroom,corridor,common_area,nursing_station]. categories in "
                      "[resident_bed,mattress,bed_rail,nurse_call,flooring,casework_door,furniture,"
                      "bathroom_safety,fall_prevention,mobility,common_area,nursing_station].")
            r = self.anthropic.complete(system=system, prompt=f"Request: {request}\nBudget: ${budget:,.0f}",
                                        model=self.s.model_route, json_mode=True, max_tokens=900)
            data = r.json()
            if data.get("rooms"):
                return data, r.model, r.tokens_in, r.tokens_out
        # heuristic decomposition (deterministic)
        data = self._heuristic_spec(request, care_type, budget)
        return data, "heuristic-local", approx_tokens(request), approx_tokens(json.dumps(data))

    def _heuristic_spec(self, request: str, care_type: str, budget: float) -> dict:
        beds = self._extract_int(request, default=30)
        return {
            "summary": f"Equip a {beds}-bed {care_type.replace('_',' ')} wing within ${budget:,.0f}, "
                       f"CMS/Life-Safety compliant.",
            "rooms": [
                {"room_type": "resident_room", "count": beds,
                 "categories": ["resident_bed", "mattress", "nurse_call", "furniture", "flooring",
                                "casework_door", "fall_prevention"]},
                {"room_type": "bathroom", "count": beds,
                 "categories": ["bathroom_safety", "nurse_call"]},
                {"room_type": "nursing_station", "count": max(1, beds // 15),
                 "categories": ["nursing_station"]},
                {"room_type": "common_area", "count": 2,
                 "categories": ["common_area", "mobility"]},
                {"room_type": "corridor", "count": 1,
                 "categories": ["flooring"]},
            ],
            "constraints": [f"Total budget ${budget:,.0f}", "CMS Appendix PP / 42 CFR §483.90",
                            "NFPA 101 (2012) Life Safety", f"{care_type} resident population"],
        }

    @staticmethod
    def _extract_int(text: str, default: int) -> int:
        m = re.search(r"(\d+)\s*[- ]?(bed|room|resident)", text.lower())
        return int(m.group(1)) if m else default

    # ------------------------------------------------------------------
    # CAPABILITY 2 — Compliance rationale (high quality / Opus) given retrieved reg
    # ------------------------------------------------------------------
    def compliance_rationale(self, item: dict, verdict: str, citation_quote: str, rule_msg: str):
        if self.anthropic and citation_quote:
            system = ("You are a senior-care compliance reviewer. Using ONLY the provided regulation "
                      "text, write a 1-2 sentence rationale for the verdict. Do not invent rules. "
                      "Quote the regulation where possible.")
            prompt = (f"Item: {item.get('name')} ({item.get('category')})\n"
                      f"Attributes: {json.dumps(item.get('attributes', {}))}\n"
                      f"Verdict: {verdict}\nRule: {rule_msg}\nRegulation text: \"{citation_quote}\"")
            r = self.anthropic.complete(system=system, prompt=prompt, model=self.s.model_reason, max_tokens=200)
            return r.text.strip(), r.model, r.tokens_in, r.tokens_out
        # heuristic rationale
        base = rule_msg or "Reviewed against retrieved regulation."
        if verdict == "VIOLATION":
            txt = f"{base} The item does not satisfy this requirement; see citation."
        elif verdict == "PASS":
            txt = f"{base} The item satisfies this requirement per the cited regulation."
        else:
            txt = "No sufficiently relevant regulation retrieved; abstaining and flagging for human review."
        return txt, "heuristic-local", approx_tokens(base), approx_tokens(txt)

    # ------------------------------------------------------------------
    # CAPABILITY 3 — Independent grounding cross-check (OpenAI). Returns True if the
    # rationale's claim is actually supported by the retrieved quote (hallucination gate).
    # ------------------------------------------------------------------
    def grounding_check(self, claim: str, quote: str):
        if not quote:
            return False, "local-keyword-rag", 0, 0
        if self.openai:
            system = ("Return JSON {\"grounded\": true|false}. grounded=true only if the CLAIM is directly "
                      "supported by the QUOTE. Be strict; unsupported claims are not grounded.")
            r = self.openai.complete(system=system, prompt=f"CLAIM: {claim}\nQUOTE: {quote}",
                                     model="gpt-4o-mini", json_mode=True, max_tokens=50)
            g = bool(r.json().get("grounded", False))
            return g, r.model, r.tokens_in, r.tokens_out
        # heuristic: require lexical overlap between claim keywords and the quote
        grounded = self._lexical_overlap(claim, quote) >= 0.12
        return grounded, "local-keyword-rag", 0, 0

    @staticmethod
    def _lexical_overlap(a: str, b: str) -> float:
        wa = set(re.findall(r"[a-z]{4,}", a.lower()))
        wb = set(re.findall(r"[a-z]{4,}", b.lower()))
        if not wa:
            return 0.0
        return len(wa & wb) / len(wa)
