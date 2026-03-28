import type { ApiResponse } from "@/types/api";
import type { DocumentMetadata, QaHistoryItem, QaResult, RetrievalResult } from "@/types/domain";
import type { WorkflowState } from "@/types/workflow";

export interface QaRequest {
  kb_id: string;
  question: string;
  top_k?: number;
}

export type QaResponse = ApiResponse<{
  result: QaResult;
  retrieval_results: RetrievalResult[];
}>;

export interface DocumentUploadRequest {
  kb_id: string;
  source: string;
  format: DocumentMetadata["format"];
}

export type DocumentUploadResponse = ApiResponse<{
  document: DocumentMetadata;
  workflow: WorkflowState;
}>;

export type DocumentListResponse = ApiResponse<{
  items: DocumentMetadata[];
  total: number;
}>;

export type QaHistoryResponse = ApiResponse<{
  items: QaHistoryItem[];
  total: number;
}>;
