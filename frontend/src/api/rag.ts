import { api } from "@/api/client";
import { buildFetchError } from "@/services/api-errors";

export type RagChunkBuildResponse = {
  schedule_id: number;
  user_id: number;
  chunks_created: number;
  embedding_dimensions: number;
  rebuilt_at: string;
  status: "success";
  message: string | null;
};

export type RagChunkBuildAllResponse = {
  user_id: number;
  schedules_considered: number;
  schedules_indexed: number;
  chunks_created: number;
  embedding_dimensions: number;
  rebuilt_at: string;
  status: "success";
  message: string | null;
};

export type RagRetrievedChunk = {
  chunk_id: number;
  schedule_id: number;
  content: string;
  score: number;
};

export type RagRetrieveResponse = {
  query: string;
  results: RagRetrievedChunk[];
};

export type RagStreamEvent =
  | { event: "meta"; data: { retrieved_chunks: number } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: { message: string } };

type RagStreamOptions = {
  topK?: number;
  sessionId?: string | null;
  baseUrl?: string;
};

export async function rebuildScheduleChunks(scheduleId: number, chunkSize = 320): Promise<RagChunkBuildResponse> {
  const response = await api.post<RagChunkBuildResponse>(`/rag/chunks/rebuild/${scheduleId}`, {
    chunk_size: chunkSize
  });
  return response.data;
}

export async function rebuildAllScheduleChunks(chunkSize = 320): Promise<RagChunkBuildAllResponse> {
  const response = await api.post<RagChunkBuildAllResponse>("/rag/chunks/rebuild-all", {
    chunk_size: chunkSize
  });
  return response.data;
}

export async function retrieveRagContext(query: string, topK = 3): Promise<RagRetrieveResponse> {
  const response = await api.post<RagRetrieveResponse>("/rag/retrieve", {
    query,
    top_k: topK
  });
  return response.data;
}

export async function* streamRagAnswer(
  query: string,
  token: string,
  options: RagStreamOptions = {}
): AsyncGenerator<RagStreamEvent> {
  const topK = options.topK ?? 3;
  const sessionId = options.sessionId?.trim() || undefined;
  const baseUrl = options.baseUrl ?? api.defaults.baseURL;
  const response = await fetch(`${baseUrl}/rag/answer/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      query,
      top_k: topK,
      ...(sessionId ? { session_id: sessionId } : {})
    })
  });
  if (!response.ok) {
    throw await buildFetchError(response, `AI 问答失败（状态码 ${response.status}）。`);
  }
  if (!response.body) {
    throw new Error("rag stream has no response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    while (buffer.includes("\n\n")) {
      const splitIndex = buffer.indexOf("\n\n");
      const chunk = buffer.slice(0, splitIndex);
      buffer = buffer.slice(splitIndex + 2);

      const eventLine = chunk.split("\n").find((line) => line.startsWith("event: "));
      const dataLine = chunk.split("\n").find((line) => line.startsWith("data: "));
      if (!eventLine || !dataLine) {
        continue;
      }

      const eventName = eventLine.replace("event: ", "").trim();
      const rawData = dataLine.replace("data: ", "").trim();
      const parsedData = JSON.parse(rawData);

      if (eventName === "meta") {
        yield { event: "meta", data: parsedData as { retrieved_chunks: number } };
      } else if (eventName === "token") {
        yield { event: "token", data: parsedData as { text: string } };
      } else if (eventName === "done") {
        yield { event: "done", data: parsedData as { message: string } };
      }
    }
  }
}
