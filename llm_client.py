# llm_client.py
"""
Use the official LangChain Groq integration.
Requires: pip install -U langchain-groq
Env: GROQ_API_KEY, GROQ_MODEL
"""

import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY missing in .env")

# Official LangChain provider for Groq
from langchain_groq import ChatGroq  # BaseChatModel under the hood
from langchain_core.messages import AIMessage

class GroqLangChain:
    """Thin wrapper so the rest of your app can call .invoke(prompt)."""

    def __init__(self, max_tokens: int = 1024, temperature: float = 0.0):
        # ChatGroq accepts model/temperature/max_tokens directly
        self._chat = ChatGroq(
            model=GROQ_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def invoke(self, prompt: str) -> AIMessage:
        # Accept a plain string prompt; ChatGroq returns an AIMessage
        return self._chat.invoke(prompt)

    def __repr__(self):
        return f"<GroqLangChain model={GROQ_MODEL}>"
