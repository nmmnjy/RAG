import { apiEndpoints } from "@/lib/api-endpoints";
import { httpGet, httpPost } from "@/lib/http";
import type { QaHistoryResponse, QaRequest, QaResponse } from "@/types/contracts";

export function askQuestion(payload: QaRequest): Promise<QaResponse> {
  return httpPost<QaRequest, QaResponse>(apiEndpoints.qa, payload);
}

export function fetchQaHistory(): Promise<QaHistoryResponse> {
  return httpGet<QaHistoryResponse>(apiEndpoints.qa_history);
}
