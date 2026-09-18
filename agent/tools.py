"""
LangChain tools for the CircuitMind conversational gateway.

Each tool wraps an existing module function unchanged. Tools that operate
on "the circuit" (explain/diagnose/export) take no circuit argument from
the LLM — they read the most recently generated/loaded circuit from the
session's circuit_store via RunnableConfig, keyed by the same thread_id
the checkpointer uses for chat history (see agent/executor.py). This
avoids asking the LLM to re-type a full circuit JSON as a tool argument,
which is unreliable. generate_circuit_tool is the one tool that writes
into circuit_store, as a side effect of its normal return.

Note: the `config: RunnableConfig` parameter on each tool is a special,
recognized name in LangGraph/LangChain's tool-execution machinery — it is
injected automatically at call time (carrying configurable.thread_id) and
stripped from the schema shown to the LLM, so the model never sees or has
to supply it. Verify this behaves as expected against your installed
langchain-core/langgraph versions before relying on it.
"""

from typing import Optional
import json

from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from generate.generate import generate_circuit
from explain.explain_module import explain_circuit
from diagnose.diagnose_module import diagnose_circuit
from export.export_module import export_module
from hint.hint_module import generate_hint

from agent.session_store import get_circuit, set_circuit


def _thread_id(config: RunnableConfig) -> str:
    """
    The thread_id passed by create_agent's checkpointer machinery — see
    agent/executor.py. Reused directly as the circuit_store key, since it's
    the same session identifier by another name.
    """
    return config["configurable"]["thread_id"]


@tool
def generate_circuit_tool(prompt: str, config: RunnableConfig) -> dict:
    """Turn a plain-English request (e.g. 'make me an LED circuit') into a
    structured circuit JSON with circuit_name, components, and connections.
    Call this first whenever the user wants a new circuit created from a
    description — it becomes 'the current circuit' for this session, so
    explain/diagnose/export can act on it afterward without needing it
    passed again."""
    result = generate_circuit(prompt)
    if "error" in result:
        return {"status": "error", "message": result["error"]}
    set_circuit(_thread_id(config), result)
    return result


@tool
def explain_circuit_tool(config: RunnableConfig) -> dict:
    """Explain the circuit currently in context for this session: what it
    does, how current flows, and any warnings. Takes no arguments — always
    operates on the most recently generated or loaded circuit. Returns an
    error if no circuit is in context yet."""
    circuit = get_circuit(_thread_id(config))
    if not circuit:
        return {"status": "error", "message": "No circuit in context yet — generate one first."}
    return explain_circuit(circuit)


@tool
def diagnose_circuit_tool(config: RunnableConfig) -> dict:
    """Check the circuit currently in context for this session for common
    electrical mistakes (missing power source, missing current-limiting
    resistor, short circuits, floating components, capacitor polarity,
    missing ground). Takes no arguments — always operates on the most
    recently generated or loaded circuit. Returns an error if none exists."""
    circuit = get_circuit(_thread_id(config))
    if not circuit:
        return {"status": "error", "message": "No circuit in context yet — generate one first."}
    return diagnose_circuit(circuit)


@tool
def export_circuit_tool(export_format: str, config: RunnableConfig) -> dict:
    """Export the circuit currently in context for this session.
    export_format must be one of: 'spice' (SPICE netlist), 'svg' (schematic
    image), 'gate_json' (logic-gate graph). Takes no circuit argument —
    always operates on the most recently generated or loaded circuit.
    Returns an error if none exists."""
    circuit = get_circuit(_thread_id(config))
    if not circuit:
        return {"status": "error", "message": "No circuit in context yet — generate one first."}
    if export_format not in {"spice", "svg", "gate_json"}:
        return {"status": "error", "message": "export_format must be one of: spice, svg, gate_json"}
    return export_module(json.dumps(circuit), export_format=export_format)


@tool
def generate_hint_tool(
    problem_title: str = "",
    problem_description: str = "",
    inputs: Optional[list[str]] = None,
    outputs: Optional[list[str]] = None,
    truth_table: Optional[list[dict]] = None,
    gates: Optional[list[dict]] = None,
    wires: Optional[list[dict]] = None,
    last_result: Optional[dict] = None,
) -> dict:
    """Give one short, non-spoiler hint for a digital-logic problem (truth
    table, input/output ports) and a student's current gate/wire graph from
    the logic-gate builder. Scoped to digital-logic gates (AND/OR/NOT/XOR/...)
    — NOT electronics components. Do not pass generate_circuit_tool's output
    here."""
    return generate_hint({
        "problem_title": problem_title,
        "problem_description": problem_description,
        "inputs": inputs or [],
        "outputs": outputs or [],
        "truth_table": truth_table or [],
        "gates": gates or [],
        "wires": wires or [],
        "last_result": last_result,
    })


ALL_TOOLS = [
    generate_circuit_tool,
    explain_circuit_tool,
    diagnose_circuit_tool,
    export_circuit_tool,
    generate_hint_tool,
]
