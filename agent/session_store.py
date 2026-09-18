"""
Session state for the CircuitMind conversational gateway.

Two independent stores, both keyed by session_id:
  - message_histories: chat transcript per session (LangChain ChatMessageHistory)
  - circuit_store: the most recently generated/loaded circuit JSON per session

In-process dicts for now. Both reset on restart and are NOT shared across
multiple uvicorn workers (the Dockerfile runs --workers 2) — fine for local
dev and single-worker deployments. For multi-worker/production, swap
message_histories for langchain_community's RedisChatMessageHistory and
circuit_store for a Redis hash, keyed the same way, using the Redis
connection you already provision via RATE_LIMIT_REDIS_URL.
"""

from langchain_community.chat_message_histories import ChatMessageHistory

message_histories: dict[str, ChatMessageHistory] = {}
circuit_store: dict[str, dict | None] = {}


def get_history(session_id: str) -> ChatMessageHistory:
    if session_id not in message_histories:
        message_histories[session_id] = ChatMessageHistory()
    return message_histories[session_id]


def get_circuit(session_id: str) -> dict | None:
    return circuit_store.get(session_id)


def set_circuit(session_id: str, circuit: dict | None) -> None:
    circuit_store[session_id] = circuit


def clear_session(session_id: str) -> None:
    message_histories.pop(session_id, None)
    circuit_store.pop(session_id, None)
