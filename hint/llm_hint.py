"""
CircuitMind - Hint Module: LLM path
hint/llm_hint.py

Groq-backed hint generation, extracted from the original hint_module.py.
Still using the raw Groq SDK for now, same as generate/llm_generate.py.
"""

import json
import os

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


_SYSTEM_PROMPT = (
    "You are a digital logic design tutor. A student is building a combinational "
    "or sequential logic circuit (gate types: AND, OR, NOT, NAND, NOR, XOR, XNOR, "
    "INPUT, OUTPUT, BUFFER) in a visual circuit builder, trying to match a truth "
    "table. You will be given the problem, its truth table, the student's CURRENT "
    "circuit graph (gates + wires), and, if available, which rows their last "
    "submit attempt failed.\n\n"
    "Reply with exactly ONE short hint (2-4 sentences, plain English) that nudges "
    "the student toward the fix. Point at the kind of mistake or the next concept "
    "to apply — do NOT give the full gate list, wiring diagram, or a complete "
    "boolean expression that hands them the answer. Be specific to what you see "
    "in their current circuit, not generic textbook text."
)


def _summarize_circuit(gates: list, wires: list) -> str:
    if not gates:
        return "The canvas is empty — no gates placed yet."

    gate_lines = []
    for g in gates:
        name = g.get("label") or f"gate{g.get('id')}"
        gate_lines.append(f"- {name}: type={g.get('type')}")

    wire_lines = []
    for w in wires or []:
        from_g = next((g for g in gates if g.get("id") == w.get("fromId")), None)
        to_g = next((g for g in gates if g.get("id") == w.get("toId")), None)
        if from_g and to_g:
            wire_lines.append(f"- {from_g.get('label')} -> {to_g.get('label')}")

    return (
        "Gates:\n" + "\n".join(gate_lines)
        + "\n\nWires:\n" + ("\n".join(wire_lines) or "(none)")
    )


def _build_user_prompt(payload: dict) -> str:
    inputs = payload.get("inputs", [])
    outputs = payload.get("outputs", [])
    truth_table = payload.get("truth_table", [])
    last_result = payload.get("last_result") or {}

    parts = [
        f"Problem: {payload.get('problem_title', 'Untitled problem')}",
        f"Description: {payload['problem_description']}" if payload.get("problem_description") else "",
        f"Inputs: {', '.join(inputs)}",
        f"Outputs: {', '.join(outputs)}",
        f"Truth table (JSON, first 16 rows): {json.dumps(truth_table[:16])}",
        "",
        "Student's current circuit:",
        _summarize_circuit(payload.get("gates", []), payload.get("wires", [])),
    ]

    failing_rows = last_result.get("failing_rows") or []
    if last_result.get("error"):
        parts.append(f"\nLast submit attempt error: {last_result['error']}")
    elif failing_rows:
        parts.append(
            f"\nLast submit attempt: {len(failing_rows)} row(s) failed: "
            f"{json.dumps(failing_rows[:5])}"
        )
    elif last_result.get("passed"):
        parts.append(
            "\nLast submit attempt passed — the student may be asking for a "
            "refinement or a different angle, not a basic fix."
        )

    return "\n".join(p for p in parts if p)


def hint_with_llm(payload: dict) -> str:
    if not GROQ_AVAILABLE:
        raise RuntimeError("Groq not installed. Run: pip install groq")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(payload)},
        ],
        max_tokens=220,
        temperature=0.4,
    )
    return completion.choices[0].message.content.strip()
