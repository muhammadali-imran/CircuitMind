"""
CircuitMind - Hint Module
hint/hint_module.py

Given a digital-logic problem (truth table, required I/O ports) and a
student's current — possibly incomplete or wrong — gate/wire graph, returns
one short, non-spoiler hint nudging them toward the fix.
Strategy: LLM (Groq) first -> rule-based fallback if unavailable.

Orchestration only — the LLM call lives in llm_hint.py, the fallback logic
lives in rule_hint.py. Mirrors the same split as generate/generate.py.
"""

import logging

from hint.llm_hint import hint_with_llm
from hint.rule_hint import hint_with_rules

logger = logging.getLogger(__name__)


def generate_hint(payload: dict) -> dict:
    """
    Main entry point.

    Supports:
    - normal hint requests
    - circuit identification requests

    Output:
    {
        "hint": str,
        "source": "llm" | "rule-based"
    }
    """
    if payload.get("request_type") == "identify":
        circuit_name = _identify_circuit(payload)

        if circuit_name != "Unknown circuit":
            return {
                "hint": f"You have created a {circuit_name} circuit.",
                "source": "rule-based",
                "circuit_name": circuit_name,
            }

    try:
        hint_text = hint_with_llm(payload)
        source = "llm"
    except Exception as e:
        logger.warning(f"LLM hint unavailable ({e}), falling back to rule-based hint")
        hint_text = hint_with_rules(payload)
        source = "rule-based"

    return {"hint": hint_text, "source": source}