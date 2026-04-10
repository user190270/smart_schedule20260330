from __future__ import annotations

import argparse
import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean, median
import time
from typing import Any
from uuid import uuid4

import httpx
from app.core.config import get_settings


TZ_SHANGHAI = timezone(timedelta(hours=8))


@dataclass
class TimedResult:
    ok: bool
    elapsed_ms: float


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    index = (len(ordered) - 1) * ratio
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def summarize(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "count": len(values),
        "mean_ms": round(mean(values), 2) if values else 0.0,
        "median_ms": round(median(values), 2) if values else 0.0,
        "p95_ms": round(percentile(ordered, 0.95), 2) if values else 0.0,
        "min_ms": round(ordered[0], 2) if values else 0.0,
        "max_ms": round(ordered[-1], 2) if values else 0.0,
    }


def make_schedule_payload(*, title: str, start_offset_minutes: int) -> dict[str, Any]:
    start = datetime.now(TZ_SHANGHAI) + timedelta(days=1, minutes=start_offset_minutes)
    end = start + timedelta(minutes=30)
    return {
        "title": title,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "location": "Lab A",
        "remark": "Performance probe payload",
        "source": "manual",
    }


async def timed_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    expected_status: int,
) -> tuple[TimedResult, httpx.Response]:
    started = time.perf_counter()
    response = await client.request(method, url, headers=headers, json=json_body)
    elapsed_ms = (time.perf_counter() - started) * 1000
    ok = response.status_code == expected_status
    return TimedResult(ok=ok, elapsed_ms=elapsed_ms), response


class PerfProbe:
    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.settings = get_settings()

    async def _register_user(self, client: httpx.AsyncClient, username_prefix: str) -> tuple[int, dict[str, str]]:
        username = f"{username_prefix}_{uuid4().hex[:8]}"
        response = await client.post(
            f"{self.base_url}/auth/register",
            json={"username": username, "password": "demo_pass_123"},
        )
        response.raise_for_status()
        body = response.json()
        token = str(body["access_token"])
        user_id = int(body["user"]["id"])
        return user_id, {"Authorization": f"Bearer {token}"}

    async def probe_crud(self, *, runs: int, warmup_runs: int) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            _, headers = await self._register_user(client, "perfcrud")

            create_timings: list[float] = []
            list_timings: list[float] = []
            update_timings: list[float] = []
            delete_timings: list[float] = []

            total_runs = warmup_runs + runs
            for index in range(total_runs):
                payload = make_schedule_payload(
                    title=f"CRUD Probe {index + 1}",
                    start_offset_minutes=index,
                )
                create_result, create_response = await timed_request(
                    client,
                    "POST",
                    f"{self.base_url}/schedules",
                    headers=headers,
                    json_body=payload,
                    expected_status=201,
                )
                create_response.raise_for_status()
                schedule_id = int(create_response.json()["id"])

                list_result, list_response = await timed_request(
                    client,
                    "GET",
                    f"{self.base_url}/schedules",
                    headers=headers,
                    expected_status=200,
                )
                list_response.raise_for_status()

                update_result, update_response = await timed_request(
                    client,
                    "PATCH",
                    f"{self.base_url}/schedules/{schedule_id}",
                    headers=headers,
                    json_body={"title": f"CRUD Probe Updated {index + 1}"},
                    expected_status=200,
                )
                update_response.raise_for_status()

                delete_result, delete_response = await timed_request(
                    client,
                    "DELETE",
                    f"{self.base_url}/schedules/{schedule_id}",
                    headers=headers,
                    expected_status=204,
                )
                delete_response.raise_for_status()

                if index < warmup_runs:
                    continue

                create_timings.append(create_result.elapsed_ms)
                list_timings.append(list_result.elapsed_ms)
                update_timings.append(update_result.elapsed_ms)
                delete_timings.append(delete_result.elapsed_ms)

            all_timings = create_timings + list_timings + update_timings + delete_timings
            return {
                "runs": runs,
                "warmup_runs": warmup_runs,
                "create": summarize(create_timings),
                "list": summarize(list_timings),
                "update": summarize(update_timings),
                "delete": summarize(delete_timings),
                "combined": summarize(all_timings),
            }

    async def probe_concurrent_reads(
        self,
        *,
        concurrency: int,
        requests_per_worker: int,
        warmup_requests: int,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            _, headers = await self._register_user(client, "perfread")

            for index in range(warmup_requests):
                payload = make_schedule_payload(
                    title=f"Read Probe Seed {index + 1}",
                    start_offset_minutes=index,
                )
                response = await client.post(f"{self.base_url}/schedules", headers=headers, json=payload)
                response.raise_for_status()

            async def worker() -> tuple[list[float], int]:
                timings: list[float] = []
                failures = 0
                for _ in range(requests_per_worker):
                    result, response = await timed_request(
                        client,
                        "GET",
                        f"{self.base_url}/schedules",
                        headers=headers,
                        expected_status=200,
                    )
                    if not result.ok:
                        failures += 1
                    else:
                        timings.append(result.elapsed_ms)
                    if response.status_code != 200:
                        continue
                return timings, failures

            started = time.perf_counter()
            results = await asyncio.gather(*(worker() for _ in range(concurrency)))
            total_elapsed = time.perf_counter() - started

            timings = [item for batch, _ in results for item in batch]
            failures = sum(failure_count for _, failure_count in results)
            total_requests = concurrency * requests_per_worker
            success_count = len(timings)
            return {
                "concurrency": concurrency,
                "requests_per_worker": requests_per_worker,
                "total_requests": total_requests,
                "success_count": success_count,
                "failure_count": failures,
                "success_rate": round((success_count / total_requests) * 100, 2) if total_requests else 0.0,
                "throughput_rps": round(total_requests / total_elapsed, 2) if total_elapsed > 0 else 0.0,
                "latency": summarize(timings),
            }

    async def _iter_sse_lines(
        self,
        client: httpx.AsyncClient,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any],
    ) -> AsyncIterator[str]:
        async with client.stream(
            "POST",
            f"{self.base_url}/rag/answer/stream",
            headers=headers,
            json=json_body,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                yield line

    async def probe_rag_stream(self, *, runs: int, warmup_runs: int) -> dict[str, Any]:
        llm_ready = all(
            [
                bool(self.settings.llm_base_url),
                bool(self.settings.llm_api_key),
                bool(self.settings.llm_chat_model),
                bool(self.settings.llm_embedding_model),
            ]
        )
        if not llm_ready:
            return {
                "skipped": True,
                "reason": "LLM runtime is not configured in the current API container.",
            }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            _, headers = await self._register_user(client, "perfrag")

            payload = make_schedule_payload(title="RAG Probe Schedule", start_offset_minutes=90)
            create_response = await client.post(
                f"{self.base_url}/schedules",
                headers=headers,
                json={**payload, "allow_rag_indexing": True},
            )
            create_response.raise_for_status()

            rebuild_response = await client.post(
                f"{self.base_url}/rag/chunks/rebuild-all",
                headers=headers,
                json={"chunk_size": 320},
            )
            rebuild_response.raise_for_status()

            first_token_timings: list[float] = []
            total_timings: list[float] = []
            total_runs = warmup_runs + runs
            for index in range(total_runs):
                stream_started = time.perf_counter()
                first_token_ms: float | None = None
                current_event: str | None = None
                async for line in self._iter_sse_lines(
                    client,
                    headers=headers,
                    json_body={
                        "query": "What is my schedule tomorrow?",
                        "top_k": 3,
                        "session_id": f"perf-rag-{index}",
                    },
                ):
                    if line.startswith("event: "):
                        current_event = line.removeprefix("event: ").strip()
                        continue
                    if line.startswith("data: ") and current_event == "token" and first_token_ms is None:
                        first_token_ms = (time.perf_counter() - stream_started) * 1000
                    if line == "":
                        continue

                total_ms = (time.perf_counter() - stream_started) * 1000
                if index < warmup_runs:
                    continue

                if first_token_ms is not None:
                    first_token_timings.append(first_token_ms)
                total_timings.append(total_ms)

            return {
                "runs": runs,
                "warmup_runs": warmup_runs,
                "first_token": summarize(first_token_timings),
                "total_stream": summarize(total_timings),
            }


async def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    probe = PerfProbe(base_url=args.base_url, timeout_seconds=args.timeout_seconds)
    crud = await probe.probe_crud(runs=args.crud_runs, warmup_runs=args.warmup_runs)
    concurrent_reads = await probe.probe_concurrent_reads(
        concurrency=args.concurrency,
        requests_per_worker=args.requests_per_worker,
        warmup_requests=args.read_seed_records,
    )
    rag_stream = await probe.probe_rag_stream(runs=args.rag_runs, warmup_runs=args.warmup_runs)
    return {
        "base_url": args.base_url,
        "crud_probe": crud,
        "concurrent_read_probe": concurrent_reads,
        "rag_stream_probe": rag_stream,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repeated local performance probes for the Smart Schedule backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--warmup-runs", type=int, default=3)
    parser.add_argument("--crud-runs", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--requests-per-worker", type=int, default=20)
    parser.add_argument("--read-seed-records", type=int, default=5)
    parser.add_argument("--rag-runs", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_probe(args))
    import json

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
