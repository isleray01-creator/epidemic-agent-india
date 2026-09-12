from __future__ import annotations

import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self._primary = None
        self._fallback = None
        self._gemini_model = None
        self._initialize()

    def _initialize(self):
        try:
            from langchain_ollama import ChatOllama
            self._primary = ChatOllama(
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                temperature=0.3,
                num_predict=2048,
            )
            logger.info(f"Initialized Ollama: {settings.ollama_model}")
        except ImportError:
            logger.warning("langchain_ollama not installed, Ollama disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama: {e}")

        if settings.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                self._gemini_model = genai.GenerativeModel("gemini-1.5-flash")
                logger.info("Initialized Gemini fallback")
            except ImportError:
                logger.warning("google-generativeai not installed, Gemini disabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

    @property
    def primary(self):
        if self._primary is None:
            raise RuntimeError("No primary LLM available (Ollama not running)")
        return self._primary

    def invoke(self, messages: list) -> str:
        try:
            response = self._primary.invoke(messages)
            return response.content
        except Exception as e:
            logger.warning(f"Primary LLM failed: {e}, trying fallback")
            return self._fallback_invoke(messages)

    def _fallback_invoke(self, messages: list) -> str:
        if self._gemini_model:
            try:
                prompt = "\n".join([f"{m.type}: {m.content}" for m in messages])
                response = self._gemini_model.generate_content(prompt)
                return response.text
            except Exception as e:
                logger.error(f"Gemini fallback failed: {e}")

        raise RuntimeError("All LLM backends failed")

    def bind_tools(self, tools: list[Any]) -> Any:
        if hasattr(self._primary, "bind_tools"):
            return self._primary.bind_tools(tools)
        return self._primary


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
