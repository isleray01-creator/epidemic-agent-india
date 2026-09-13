from __future__ import annotations

import json
import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self._client = None
        self._model = "gemini-3.6-flash"
        self._initialize()

    def _initialize(self):
        if not settings.gemini_api_key:
            logger.warning("No GEMINI_API_KEY set")
            return

        try:
            from google import genai
            self._client = genai.Client(api_key=settings.gemini_api_key)
            logger.info(f"Initialized Gemini client with model {self._model}")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}")

    @property
    def available(self) -> bool:
        return self._client is not None

    def invoke(self, messages: list) -> str:
        if not self.available:
            raise RuntimeError("No LLM available - GEMINI_API_KEY not set or invalid")

        system_msg = ""
        user_parts = []
        for m in messages:
            if hasattr(m, "type"):
                if m.type == "system":
                    system_msg = m.content
                else:
                    user_parts.append(m.content)
            elif isinstance(m, dict):
                role = m.get("role", "user")
                content = m.get("content", "")
                if role == "system":
                    system_msg = content
                else:
                    user_parts.append(content)
            else:
                user_parts.append(str(m))

        prompt = "\n\n".join(user_parts)
        if system_msg:
            prompt = f"{system_msg}\n\n{prompt}"

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini call failed: {e}")
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
