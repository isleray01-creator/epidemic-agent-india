from __future__ import annotations

import json
import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self._model = None
        self._initialize()

    def _initialize(self):
        if settings.gemini_api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self._model = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=settings.gemini_api_key,
                    temperature=0.3,
                    max_output_tokens=2048,
                )
                logger.info("Initialized Gemini 1.5 Flash via langchain")
            except ImportError:
                logger.warning("langchain-google-genai not installed")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")

    @property
    def available(self) -> bool:
        return self._model is not None

    def invoke(self, messages: list) -> str:
        if not self.available:
            raise RuntimeError("No LLM available - Gemini not initialized")
        try:
            response = self._model.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise

    def invoke_json(self, messages: list) -> dict[str, Any]:
        raw = self.invoke(messages)
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            return {"raw_response": text}


_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
