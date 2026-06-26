"""Compliance rule engine. Deterministic attribute rules (loaded from
compliance_rules.json) give reliable, citable verdicts for the planted-violation
demo and the eval harness; RAG + the LLM add natural-language rationale and catch
the long tail. Every asserted verdict must be grounded in a retrieved reg chunk or
it is downgraded to ABSTAIN by the hallucination gate."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from .config import Settings


@dataclass
class Rule:
    rule_id: str
    category: str
    predicate: dict
    citation: str
    reg_id: str
    message: str
    applies_when: dict


def load_rules(settings: Settings) -> list[Rule]:
    raw = json.loads(settings.rules_json.read_text("utf-8"))
    return [Rule(rule_id=r["rule_id"], category=r["category"], predicate=r["predicate"],
                 citation=r["citation"], reg_id=r["reg_id"], message=r["message"],
                 applies_when=r.get("applies_when", {})) for r in raw]


def _applies(rule: Rule, item: dict) -> bool:
    if rule.category != "*" and rule.category != item.get("category"):
        return False
    aw = rule.applies_when
    if "subcategory" in aw and aw["subcategory"] != item.get("subcategory"):
        return False
    if "applicable_rooms_includes" in aw:
        rooms = item.get("applicable_rooms") or item.get("applicableRooms") or []
        if aw["applicable_rooms_includes"] not in rooms:
            return False
    return True


def _check_predicate(pred: dict, attrs: dict) -> tuple[bool, str]:
    """Returns (passed, detail). Supports exact, *_min, *_range predicates.

    A *missing* attribute is treated as "not assessable" and does NOT fail the rule
    — we only assert a VIOLATION when the catalog gives explicit evidence of
    non-compliance (e.g. cleanable_surface=False, clear_width_in=36). Unknowns are
    left to the RAG/abstain path rather than producing false positives."""
    for key, expected in pred.items():
        if key.endswith("_min"):
            attr = key[:-4]
            val = attrs.get(attr)
            if val is None:
                continue
            if float(val) < float(expected):
                return False, f"{attr}={val} < min {expected}"
        elif key.endswith("_range"):
            attr = key[:-6]
            val = attrs.get(attr)
            if val is None:
                continue
            lo, hi = expected
            if not (lo <= float(val) <= hi):
                return False, f"{attr}={val} outside [{lo},{hi}]"
        else:
            val = attrs.get(key)
            if val is None:
                continue
            if val != expected:
                return False, f"{key}={val} (expected {expected})"
    return True, "all attribute checks passed"


@dataclass
class RuleResult:
    rule: Rule
    passed: bool
    detail: str


def evaluate_item_rules(item: dict, rules: list[Rule]) -> list[RuleResult]:
    attrs = item.get("attributes", {}) or {}
    out: list[RuleResult] = []
    for rule in rules:
        if not _applies(rule, item):
            continue
        passed, detail = _check_predicate(rule.predicate, attrs)
        out.append(RuleResult(rule=rule, passed=passed, detail=detail))
    return out
