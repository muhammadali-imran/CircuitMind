"""
CircuitMind - Generate Module
generate/generate.py

Converts a natural language prompt into a structured circuit JSON.
Strategy: LLM (Groq) first -> rule-based fallback if LLM is unavailable.

Orchestration only — the LLM call lives in llm_generate.py, the fallback
templates live in rule_templates.py. This split keeps the rule-based path
trivially unit-testable in isolation from the LLM path, and means the
public generate_circuit() signature (and agent/tools.py's use of it) never
has to change regardless of what generate_with_llm() does internally.
"""

import logging

from generate.llm_generate import generate_with_llm
from generate.rule_templates import generate_with_rules

logger = logging.getLogger(__name__)


def validate_input(prompt: str) -> str:
    if not prompt or len(prompt.strip()) == 0:
        raise ValueError("Input cannot be empty. Try: 'make me a LED circuit'")
    if len(prompt.strip()) < 3:
        raise ValueError("Input too short. Try: 'make me a LED circuit'")
    if len(prompt) > 1000:
        raise ValueError("Input too long. Keep it under 1000 characters.")
    return prompt.strip()


def generate_circuit(user_prompt: str) -> dict:
    """
    Main entry point.
    Input:  user text e.g. 'make me a LED circuit'
    Output: circuit JSON dict — never raises, always returns.
    """
    try:
        clean_prompt = validate_input(user_prompt)
    except ValueError as e:
        return {"error": str(e), "error_code": "INVALID_INPUT", "components": [], "connections": []}

    try:
        logger.info("Attempting LLM generation via Groq")
        return generate_with_llm(clean_prompt)
    except Exception as e:
        logger.warning(f"LLM unavailable ({e}), falling back to rule-based generation")
        return generate_with_rules(clean_prompt)
