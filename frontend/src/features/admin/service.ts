import { apiEndpoints } from "@/lib/api-endpoints";
import { httpGet } from "@/lib/http";
import type { DocumentListResponse } from "@/types/contracts";
import type { ApiResponse } from "@/types/api";
import type { WorkflowState } from "@/types/workflow";

export function fetchDocuments(): Promise<DocumentListResponse> {
  return httpGet<DocumentListResponse>(apiEndpoints.documents);
}

export function fetchTasks(): Promise<ApiResponse<{ items: WorkflowState[]; total: number }>> {
  return httpGet<ApiResponse<{ items: WorkflowState[]; total: number }>>(apiEndpoints.tasks);
}
