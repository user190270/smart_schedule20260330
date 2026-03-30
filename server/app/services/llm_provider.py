from __future__ import annotations

from dataclasses import dataclass
import json
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from app.core.config import get_settings


class LlmProviderError(RuntimeError):
    pass


@dataclass
class OpenAICompatibleProvider:
    base_url: str
    api_key: str
    chat_model: str
    embedding_model: str
    embedding_dimensions: int
    timeout_seconds: int = 40

    @classmethod
    def from_settings(cls) -> "OpenAICompatibleProvider":
        settings = get_settings()
        if not settings.llm_base_url:
            raise LlmProviderError("LLM_BASE_URL is not configured.")
        if not settings.llm_api_key:
            raise LlmProviderError("LLM_API_KEY is not configured.")
        if not settings.llm_chat_model:
            raise LlmProviderError("LLM_CHAT_MODEL is not configured.")
        if not settings.llm_embedding_model:
            raise LlmProviderError("LLM_EMBEDDING_MODEL is not configured.")
        return cls(
            base_url=settings.llm_base_url.rstrip("/"),
            api_key=settings.llm_api_key,
            chat_model=settings.llm_chat_model,
            embedding_model=settings.llm_embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
        )

    def _build_url(self, endpoint: str) -> str:
        normalized = endpoint.lstrip("/")
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/{normalized}"
        return f"{self.base_url}/v1/{normalized}"

    def _post_json(self, endpoint: str, payload: dict) -> dict:
        raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib_request.Request(
            url=self._build_url(endpoint),
            data=raw_body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise LlmProviderError(f"LLM upstream HTTP error: {exc.code} {detail}") from exc
        except URLError as exc:
            raise LlmProviderError(f"LLM upstream request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LlmProviderError("LLM upstream request timed out.") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise LlmProviderError("LLM upstream returned non-JSON payload.") from exc

    def create_chat_completion(self, messages: list[dict], temperature: float = 0) -> str:
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        response = self._post_json("chat/completions", payload)
        try:
            return str(response["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmProviderError("Invalid chat completion response format.") from exc

    def create_embedding(self, text: str) -> list[float]:
        payload = {
            "model": self.embedding_model,
            "input": text,
        }
        response = self._post_json("embeddings", payload)
        try:
            embedding = response["data"][0]["embedding"]
            if not isinstance(embedding, list) or not embedding:
                raise TypeError("embedding should be non-empty list")
            normalized = [float(value) for value in embedding]
            if len(normalized) != self.embedding_dimensions:
                raise LlmProviderError(
                    "Embedding dimensions mismatch: "
                    f"expected {self.embedding_dimensions}, got {len(normalized)}."
                )
            return normalized
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LlmProviderError("Invalid embedding response format.") from exc
