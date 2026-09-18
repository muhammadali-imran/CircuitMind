"""
CircuitMind - Gateway Agent Tests
tests/test_agent.py

Tests the tool layer directly (no live LLM calls) — verifies tools read and
write session state correctly and fail gracefully with no circuit yet in
context. Full agent routing (which tool the LLM actually picks for a given
message) needs a live Groq call and isn't covered here; consider a separate,
opt-in integration test for that if you want CI coverage on routing
accuracy too.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import (
    generate_circuit_tool,
    explain_circuit_tool,
    diagnose_circuit_tool,
    export_circuit_tool,
    generate_hint_tool,
    ALL_TOOLS,
)
from agent.session_store import clear_session, get_circuit


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def test_all_tools_have_unique_names():
    names = [t.name for t in ALL_TOOLS]
    assert len(names) == len(set(names))


def test_explain_without_circuit_returns_error():
    clear_session("test-session-explain")
    result = explain_circuit_tool.invoke({}, config=_config("test-session-explain"))
    assert result["status"] == "error"


def test_diagnose_without_circuit_returns_error():
    clear_session("test-session-diagnose")
    result = diagnose_circuit_tool.invoke({}, config=_config("test-session-diagnose"))
    assert result["status"] == "error"


def test_export_without_circuit_returns_error():
    clear_session("test-session-export")
    result = export_circuit_tool.invoke(
        {"export_format": "spice"}, config=_config("test-session-export")
    )
    assert result["status"] == "error"


def test_export_rejects_invalid_format():
    session_id = "test-session-export-invalid"
    clear_session(session_id)
    generate_circuit_tool.invoke({"prompt": "make me a LED circuit"}, config=_config(session_id))
    result = export_circuit_tool.invoke({"export_format": "pdf"}, config=_config(session_id))
    assert result["status"] == "error"


def test_generate_then_diagnose_uses_session_circuit():
    session_id = "test-session-generate-diagnose"
    clear_session(session_id)

    generate_circuit_tool.invoke(
        {"prompt": "make me a LED circuit"}, config=_config(session_id)
    )
    assert get_circuit(session_id) is not None

    result = diagnose_circuit_tool.invoke({}, config=_config(session_id))
    assert "passed" in result


def test_sessions_do_not_share_circuits():
    session_a, session_b = "test-session-a", "test-session-b"
    clear_session(session_a)
    clear_session(session_b)

    generate_circuit_tool.invoke({"prompt": "make me a LED circuit"}, config=_config(session_a))

    assert get_circuit(session_a) is not None
    assert get_circuit(session_b) is None


def test_hint_tool_runs_without_a_circuit():
    result = generate_hint_tool.invoke({
        "problem_title": "Half Adder",
        "inputs": ["A", "B"],
        "outputs": ["S", "C"],
        "gates": [],
        "wires": [],
    })
    assert isinstance(result.get("hint"), str) and result["hint"]
