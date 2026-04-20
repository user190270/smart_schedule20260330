from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
import json
from typing import Any, TypeVar

from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel

from app.core.config import get_settings


class AiRuntimeUnavailable(RuntimeError):
    pass


class AiRuntimeError(RuntimeError):
    pass


StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)


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

    def _build_chat_model(self, *, temperature: float) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.chat_model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=temperature,
            timeout=self.timeout_seconds,
        )

    def _build_embeddings_client(self) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            model=self.embedding_model,
            api_key=self.api_key,
            base_url=self.base_url,
            request_timeout=self.timeout_seconds,
        )

    @staticmethod
    def _serialize_payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, default=str)

    @staticmethod
    def _normalize_exception(exc: Exception) -> str:
        message = str(exc).strip()
        return message or "AI upstream request failed."

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
        chain = prompt | self._build_chat_model(temperature=temperature) | parser

        try:
            raw_result = await chain.ainvoke({"payload_json": self._serialize_payload(human_payload)})
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc

        try:
            return output_model.model_validate(raw_result)
        except Exception as exc:
            raise AiRuntimeError("Invalid structured AI output.") from exc

    async def ainvoke_text(
        self,
        *,
        system_prompt: str,
        human_payload: dict[str, Any],
        temperature: float = 0.2,
    ) -> str:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                ("human", "{payload_json}"),
            ]
        ).partial(system_prompt=system_prompt)
        chain = prompt | self._build_chat_model(temperature=temperature) | StrOutputParser()

        try:
            result = await chain.ainvoke({"payload_json": self._serialize_payload(human_payload)})
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc
        return str(result).strip()

    async def astream_text(
        self,
        *,
        system_prompt: str,
        human_payload: dict[str, Any],
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "{system_prompt}"),
                ("human", "{payload_json}"),
            ]
        ).partial(system_prompt=system_prompt)
        chain = prompt | self._build_chat_model(temperature=temperature) | StrOutputParser()

        try:
            async for chunk in chain.astream({"payload_json": self._serialize_payload(human_payload)}):
                text = str(chunk)
                if text:
                    yield text
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc

    async def aembed_query(self, text: str) -> list[float]:
        try:
            embedding = await self._build_embeddings_client().aembed_query(text)
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc
        return self._validate_embedding(embedding)

    async def aembed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            embeddings = await self._build_embeddings_client().aembed_documents(list(texts))
        except Exception as exc:
            raise AiRuntimeError(self._normalize_exception(exc)) from exc
        return [self._validate_embedding(item) for item in embeddings]
