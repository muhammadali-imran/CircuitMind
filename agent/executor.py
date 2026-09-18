"""
The CircuitMind gateway agent: a tool-calling agent wrapped with
per-session chat history via RunnableWithMessageHistory.

This is what api/app.py's single /chat route invokes. session_id (passed
as configurable.session_id) is what ties a request to its chat history
(agent/session_store.get_history) and its current circuit
(agent/session_store.circuit_store) — both threaded through automatically
by RunnableWithMessageHistory and the tools' RunnableConfig injection,
respectively.
"""

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.runnables.history import RunnableWithMessageHistory

from agent.llm import llm
from agent.prompt import prompt
from agent.tools import ALL_TOOLS
from agent.session_store import get_history

_agent = create_tool_calling_agent(llm, ALL_TOOLS, prompt)
_executor = AgentExecutor(agent=_agent, tools=ALL_TOOLS, verbose=False)

conversational_agent = RunnableWithMessageHistory(
    _executor,
    get_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)
