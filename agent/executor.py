"""
The CircuitMind gateway agent.

Built on LangChain's create_agent (LangChain >= 1.0), which runs on
LangGraph under the hood. Statefulness — both chat history and, via
agent/tools.py's RunnableConfig-injected reads/writes, the current
circuit — is keyed by thread_id (passed as config={"configurable":
{"thread_id": session_id}} on each invoke).

InMemorySaver keeps everything in-process: history resets on restart and
isn't shared across multiple uvicorn workers (Dockerfile runs --workers 2).
For production, swap it for a persistent checkpointer — e.g.
langgraph.checkpoint.postgres.PostgresSaver or a Redis-backed one — using
the Redis connection you already provision via RATE_LIMIT_REDIS_URL.
"""

from langchain.agents import create_agent

try:
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError:  # older langgraph versions used this name
    from langgraph.checkpoint.memory import MemorySaver as InMemorySaver

from agent.llm import llm
from agent.prompt import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS

checkpointer = InMemorySaver()

conversational_agent = create_agent(
    model=llm,
    tools=ALL_TOOLS,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
)


def run_chat_turn(session_id: str, message: str) -> str:
    """
    Invoke the agent for one turn of a session and return the assistant's
    reply text. Chat history for this session_id is handled automatically
    by the checkpointer via thread_id — nothing to pass explicitly.
    """
    result = conversational_agent.invoke(
        {"messages": [{"role": "user", "content": message}]},
        config={"configurable": {"thread_id": session_id}},
    )
    return result["messages"][-1].content
