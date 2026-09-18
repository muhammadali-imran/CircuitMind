"""
Session state for the CircuitMind conversational gateway.

Chat history is no longer tracked here — as of the LangChain 1.0
create_agent API (agent/executor.py), it's handled automatically by the
graph's checkpointer, keyed by thread_id. What's left to manage manually is
the one piece create_agent doesn't know about: the current circuit.

circuit_store is keyed by the same id used as thread_id (session_id from
api/app.py / app_streamlit.py) — the two are the same identifier, just
named per their role at each call site.

In-process dict for now — resets on restart, not shared across multiple
uvicorn workers (the Dockerfile runs --workers 2). For multi-worker/
production use, swap for a Redis hash keyed the same way, using the Redis
connection you already provision via RATE_LIMIT_REDIS_URL.
"""

circuit_store: dict[str, dict | None] = {}


def get_circuit(session_id: str) -> dict | None:
    return circuit_store.get(session_id)


def set_circuit(session_id: str, circuit: dict | None) -> None:
    circuit_store[session_id] = circuit


def clear_session(session_id: str) -> None:
    """
    Clears the current-circuit state for this session. Does NOT clear chat
    history in the checkpointer — the simplest way to reset a
    conversation's history is for the caller to start using a new
    session_id/thread_id (both app_streamlit.py and api/app.py's callers
    are expected to do this on an explicit reset).
    """
    circuit_store.pop(session_id, None)
