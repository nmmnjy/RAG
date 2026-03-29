import type { ApiResponse } from "@/types/api";
import type { DocumentMetadata, QaHistoryItem, QaResult } from "@/types/domain";
import type { WorkflowState } from "@/types/workflow";

export interface QaRequest {
  kb_id: string;
  query_text: string;
  top_k?: number;
  vector_top_k?: number;
  keyword_top_k?: number;
  enable_rerank?: boolean;
}

export type QaResponse = ApiResponse<QaResult>;

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
