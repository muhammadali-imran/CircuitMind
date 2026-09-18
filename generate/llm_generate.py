"""
CircuitMind - Generate Module: LLM path
generate/llm_generate.py

Groq-backed circuit generation, extracted from the original generate.py.
Still using the raw Groq SDK for now — this is the natural place to swap
in ChatGroq + LangChain structured output once that conversion happens;
generate.py's orchestration and agent/tools.py's generate_circuit_tool
don't need to change when it does, since both just call
generate_with_llm(prompt) -> dict.
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
    "You are a circuit generator AI. "
    "Convert user requests into circuit JSON. "
    "Reply ONLY with valid JSON — no explanation, no markdown, no code blocks.\n"
    "IMPORTANT: Use ONLY these exact component names — no prefixes, values, or modifiers:\n"
    "battery, power_supply, solar_cell, resistor, capacitor, inductor, potentiometer, "
    "diode, led, zener_diode, transistor, npn_transistor, pnp_transistor, mosfet, "
    "op_amp, 555_timer, arduino, microcontroller, "
    "buzzer, motor, dc_motor, speaker, relay, display, lcd, "
    "ldr, thermistor, photodiode, button, switch, sensor, "
    "ground, fuse, transformer"
)

_USER_TEMPLATE = (
    'Convert this into a circuit JSON:\n\n"{prompt}"\n\n'
    "Use exactly this format:\n"
    '{{\n'
    '  "circuit_name": "name of circuit",\n'
    '  "components": ["component1", "component2"],\n'
    '  "connections": ["comp1 -> comp2 -> comp3"],\n'
    '  "confidence": "high",\n'
    '  "description": "one line explanation"\n'
    '}}'
)


def generate_with_llm(prompt: str) -> dict:
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
            {"role": "user",   "content": _USER_TEMPLATE.format(prompt=prompt)},
        ],
        max_tokens=512,
        temperature=0.2,
    )

    raw = completion.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw

    result = json.loads(raw)   # raises JSONDecodeError if invalid
    result["source"] = "llm"
    return result
