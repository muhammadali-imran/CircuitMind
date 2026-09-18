"""
CircuitMind - Hint Module: rule-based fallback
hint/rule_hint.py

Deterministic hint checks (empty canvas, missing I/O gates, floating
gates), used when the LLM path is unavailable. Extracted from the original
hint_module.py — logic unchanged, just renamed from the private
_hint_with_rules to the public hint_with_rules since it now lives in its
own module.
"""


def hint_with_rules(payload: dict) -> str:
    gates = payload.get("gates", [])
    wires = payload.get("wires", [])
    inputs = payload.get("inputs", [])
    outputs = payload.get("outputs", [])

    if not gates:
        return (
            f"Start by placing {len(inputs)} INPUT gate(s) named exactly "
            f"{', '.join(inputs) or '(see problem)'} and {len(outputs)} OUTPUT "
            f"gate(s) named {', '.join(outputs) or '(see problem)'} — then wire "
            "logic gates between them."
        )

    input_gates = [g for g in gates if g.get("type") == "INPUT"]
    output_gates = [g for g in gates if g.get("type") == "OUTPUT"]
    if len(input_gates) < len(inputs) or len(output_gates) < len(outputs):
        return (
            f"Your circuit has {len(input_gates)} INPUT and {len(output_gates)} "
            f"OUTPUT gate(s), but this problem needs {len(inputs)} and "
            f"{len(outputs)}. Add the missing ones and label them to match."
        )

    wired_ids = {w.get("fromId") for w in wires} | {w.get("toId") for w in wires}
    floating = [g for g in gates if g.get("id") not in wired_ids]
    if floating:
        names = ", ".join(g.get("label", "?") for g in floating)
        return (
            f"'{names}' isn't connected to anything yet — a floating gate can't "
            "affect the output. Wire it in."
        )

    return (
        "Gate and wire counts look reasonable — walk through the truth table row "
        "by row and check whether your gate types (AND/OR/XOR/NOT) match what "
        "each row actually needs on the path from input to output."
    )
