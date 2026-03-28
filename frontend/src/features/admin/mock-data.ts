import type { ApiSuccessResponse } from "@/types/api";
import type { DocumentMetadata } from "@/types/domain";

export const demoDocuments: DocumentMetadata[] = [
  {
    doc_id: "doc_001",
    kb_id: "kb_hr",
    source: "employee-handbook.pdf",
    format: "pdf",
    version: "v1",
    status: "indexed"
  },
  {
    doc_id: "doc_002",
    kb_id: "kb_fin",
    source: "expense-rule.md",
    format: "md",
    version: "v3",
    status: "parsing"
  }
];

export const demoDocumentListResponse: ApiSuccessResponse<{ items: DocumentMetadata[]; total: number }> = {
  code: "OK",
  message: "success",
  data: {
    items: demoDocuments,
    total: demoDocuments.length
  },
  request_id: "req_doc_001",
  trace_id: "trace_doc_001",
  ts: "2026-03-28T10:20:00Z"
};
