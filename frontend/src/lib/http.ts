import type { ApiErrorResponse, ApiResponse } from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

interface HttpRequestOptions {
  timeoutMs?: number;
}

function buildAbortSignal(timeoutMs?: number): { signal?: AbortSignal; release: () => void } {
  if (!timeoutMs || timeoutMs <= 0) {
    return { signal: undefined, release: () => undefined };
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    release: () => clearTimeout(timer)
  };
}

export async function httpPost<TRequest, TResponse>(path: string, payload: TRequest, options?: HttpRequestOptions): Promise<TResponse> {
  const { signal, release } = buildAbortSignal(options?.timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal
    });
    const data = (await response.json()) as TResponse;
    return data;
  } finally {
    release();
  }
}

export async function httpGet<TResponse>(path: string): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" }
  });
  const data = (await response.json()) as TResponse;
  return data;
}

export function isApiError<T>(result: ApiResponse<T>): result is ApiErrorResponse {
  return !("data" in result);
}
