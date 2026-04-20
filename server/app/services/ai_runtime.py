from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any, TypeVar

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel

from app.core.config import get_settings


class AiRuntimeUnavailable(RuntimeError):
    pass


class AiRuntimeError(RuntimeError):
    pass


StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)
UsageCallback = Callable[["TokenUsage"], None]


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __bool__(self) -> bool:
        return self.total_tokens > 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )

    @staticmethod
    def _as_int(value: Any) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        return 0

    @classmethod
    def from_chat_usage_metadata(cls, usage_metadata: Mapping[str, Any] | None) -> "TokenUsage":
        if not usage_metadata:
            return cls()

        input_tokens = cls._as_int(usage_metadata.get("input_tokens") or usage_metadata.get("prompt_tokens"))
        output_tokens = cls._as_int(
            usage_metadata.get("output_tokens") or usage_metadata.get("completion_tokens")
        )
        total_tokens = cls._as_int(usage_metadata.get("total_tokens"))
        if total_tokens <= 0:
            total_tokens = input_tokens + output_tokens
        return cls(
            input_tokens=max(0, input_tokens),
            output_tokens=max(0, output_tokens),
            total_tokens=max(0, total_tokens),
        )

    @classmethod
    def from_openai_usage(cls, usage: Mapping[str, Any] | None) -> "TokenUsage":
        if not usage:
            return cls()

        input_tokens = cls._as_int(usage.get("prompt_tokens") or usage.get("input_tokens"))
        output_tokens = cls._as_int(usage.get("completion_tokens") or usage.get("output_tokens"))
        total_tokens = cls._as_int(usage.get("total_tokens"))
        if total_tokens <= 0:
            total_tokens = input_tokens + output_tokens
        return cls(
            input_tokens=max(0, input_tokens),
            output_tokens=max(0, output_tokens),
            total_tokens=max(0, total_tokens),
        )


@dataclass
class LangChainAiRuntime:
    base_url: str
    api_key: str
    chat_model: str
    embedding_model: str
    embedding_dimensions: int
    timeout_seconds: int = 15

    @classmethod
    def from_settings(cls) -> "LangChainAiRuntime":
        settings = get_settings()
        if not settings.llm_base_url:
            raise AiRuntimeUnavailable("LLM_BASE_URL is not configured.")
        if not settings.llm_api_key:
            raise AiRuntimeUnavailable("LLM_API_KEY is not configured.")
        if not settings.llm_chat_model:
            raise AiRuntimeUnavailable("LLM_CHAT_MODEL is not configured.")
        if not settings.llm_embedding_model:
            raise AiRuntimeUnavailable("LLM_EMBEDDING_MODEL is not configured.")
        return cls(
            base_url=settings.llm_base_url.rstrip("/"),
            api_key=settings.llm_api_key,
            chat_model=settings.llm_chat_model,
            embedding_model=settings.llm_embedding_model,
            embedding_dimensions=settings.embedding_dimensions,
        )

    def _build_chat_model(self, *, temperature: float, stream_usage: bool | None = None) -> ChatOpenAI:
        model_kwargs: dict[str, Any] = {
            "model": self.chat_model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "temperature": temperature,
            "timeout": self.timeout_seconds,
        }
        if stream_usage is not None:
            model_kwargs["stream_usage"] = stream_usage
        return ChatOpenAI(**model_kwargs)

    def _build_embeddings_client(self) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            model=self.embedding_model,
            api_key=self.api_key,
            base_url=self.base_url,
            request_timeout=self.timeout_seconds,
            dimensions=self.embedding_dimensions,
        )

    def _embedding_request_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"model": self.embedding_model}
        if self.embedding_dimensions > 0:
            params["dimensions"] = self.embedding_dimensions
        return params

    @staticmethod
    def _serialize_payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _normalize_exception(exc: Exception) -> str:
        message = str(exc).strip()
        return message or "AI upstream request failed."

    @staticmethod
    def _notify_usage(usage_callback: UsageCallback | None, usage: TokenUsage) -> None:
        if usage_callback is not None and usage:
            usage_callback(usage)

    @staticmethod
    def _message_text_content(message: Any) -> str:
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return str(content)

    def _validate_embedding(self, embedding: Sequence[float]) -> list[float]:
        normalized = [float(value) for value in embedding]
        if len(normalized) != self.embedding_dimensions:
            raise AiRuntimeError(
                "Embedding dimensions mismatch: "
                f"expected {self.embedding_dimensions}, got {len(normalized)}."
            )
        return normalized

    async def ainvoke_structured_output(
        self,
        *,
        system_prompt: str,
        human_payload: dict[str, Any],
        output_model: type[StructuredOutputT],
        temperature: float = 0,
        usage_callback: UsageCallback | None = None,
    ) -> StructuredOutputT:
        parser = JsonOutputParser(pydantic_object=output_model)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}\n\n{format_instructions}"),
                ("human", "{payload_json}"),
            ]
        ).partial(
            system_prompt=system_prompt,
            format_instructions=parser.get_format_instructions(),
        )
        messages = prompt.format_messages(payload_json=self._serialize_payload(human_payload))

        try:
            message = await self._build_chat_model(temperature=temperature).ainvoke(messages)
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc

        self._notify_usage(usage_callback, TokenUsage.from_chat_usage_metadata(getattr(message, "usage_metadata", None)))

        try:
            parsed = parser.parse(self._message_text_content(message))
            return output_model.model_validate(parsed)
        except Exception as exc:
            raise AiRuntimeError("Invalid structured AI output.") from exc

    async def ainvoke_text(
        self,
        *,
        system_prompt: str,
        human_payload: dict[str, Any],
        temperature: float = 0.2,
        usage_callback: UsageCallback | None = None,
    ) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                ("human", "{payload_json}"),
            ]
        ).partial(system_prompt=system_prompt)
        messages = prompt.format_messages(payload_json=self._serialize_payload(human_payload))

        try:
            message = await self._build_chat_model(temperature=temperature).ainvoke(messages)
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc

        self._notify_usage(usage_callback, TokenUsage.from_chat_usage_metadata(getattr(message, "usage_metadata", None)))
        return self._message_text_content(message).strip()

    async def astream_text(
        self,
        *,
        system_prompt: str,
        human_payload: dict[str, Any],
        temperature: float = 0.2,
        usage_callback: UsageCallback | None = None,
    ) -> AsyncIterator[str]:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                ("human", "{payload_json}"),
            ]
        ).partial(system_prompt=system_prompt)
        messages = prompt.format_messages(payload_json=self._serialize_payload(human_payload))

        try:
            async for chunk in self._build_chat_model(temperature=temperature, stream_usage=True).astream(messages):
                self._notify_usage(
                    usage_callback,
                    TokenUsage.from_chat_usage_metadata(getattr(chunk, "usage_metadata", None)),
                )
                text = self._message_text_content(chunk).strip()
                if text:
                    yield text
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc

    async def aembed_query(
        self,
        text: str,
        *,
        usage_callback: UsageCallback | None = None,
    ) -> list[float]:
        embeddings = await self.aembed_documents([text], usage_callback=usage_callback)
        return embeddings[0]

    async def aembed_documents(
        self,
        texts: Sequence[str],
        *,
        usage_callback: UsageCallback | None = None,
    ) -> list[list[float]]:
        values = list(texts)
        if not values:
            return []

        client = self._build_embeddings_client()
        chunk_size = client.chunk_size or len(values)
        params = self._embedding_request_params()
        embeddings: list[list[float]] = []
        total_usage = TokenUsage()

        try:
            for start in range(0, len(values), chunk_size):
                response = await client.async_client.create(input=values[start : start + chunk_size], **params)
                payload = response if isinstance(response, dict) else response.model_dump()
                total_usage += TokenUsage.from_openai_usage(payload.get("usage"))
                embeddings.extend(self._validate_embedding(item["embedding"]) for item in payload["data"])
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc

        self._notify_usage(usage_callback, total_usage)
        return embeddings
