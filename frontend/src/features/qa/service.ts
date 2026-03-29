import { apiEndpoints } from "@/lib/api-endpoints";
import { httpGet, httpPost } from "@/lib/http";
import type { ApiResponse } from "@/types/api";
import type { QaHistoryResponse, QaRequest, QaResponse } from "@/types/contracts";

export async function askQuestion(payload: QaRequest): Promise<QaResponse> {
  try {
    const response = await httpPost<QaRequest, QaResponse>(apiEndpoints.qa, payload, { timeoutMs: 12000 });
    return response;
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      const timeoutError: ApiResponse<never> = {
        code: "RETR_TIMEOUT",
        message: "qa request timeout",
        request_id: "req_frontend_qa_timeout",
        trace_id: "trace_frontend_qa_timeout"
      };
      return timeoutError;
    }
    const networkError: ApiResponse<never> = {
      code: "COMMON_INTERNAL_ERROR",
      message: "qa request failed: unable to reach backend /api/v1/qa/answers",
      request_id: "req_frontend_qa_request_failed",
      trace_id: "trace_frontend_qa_request_failed"
    };
    return networkError;
  }
}

export function fetchQaHistory(): Promise<QaHistoryResponse> {
  return httpGet<QaHistoryResponse>(apiEndpoints.qa_history);
}
