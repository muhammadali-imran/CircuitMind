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
    Input:  dict with problem_title, problem_description, inputs, outputs,
            truth_table, gates, wires, last_result (all optional).
    Output: { "hint": str, "source": "llm" | "rule-based" } — never raises.
    """
    try:
        hint_text = hint_with_llm(payload)
        source = "llm"
    except Exception as e:
        logger.warning(f"LLM hint unavailable ({e}), falling back to rule-based hint")
        hint_text = hint_with_rules(payload)
        source = "rule-based"

    return {"hint": hint_text, "source": source}
