"""ChatGroq model instance for the CircuitMind gateway agent."""

from langchain_groq import ChatGroq

from settings import settings

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=settings.groq_api_key,
    temperature=0.2,
)
