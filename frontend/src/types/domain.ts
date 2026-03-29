export type DocumentStatus = "uploaded" | "parsing" | "parsed" | "indexing" | "indexed" | "failed";

export interface DocumentMetadata {
  doc_id: string;
  kb_id: string;
  source: string;
  format: "pdf" | "docx" | "xlsx" | "md" | "txt";
  version: string;
  status: DocumentStatus;
}

export interface ChunkData {
  chunk_id: string;
  doc_id: string;
  content: string;
  token_count: number;
  section_path: string[];
}

export interface Citation {
  citation_id: string;
  chunk_id: string;
  doc_id: string;
  kb_id: string;
  section_path: string[];
  snippet: string;
  score_final: number;
  source: string | null;
  citation: Record<string, unknown>;
}

export interface RetrievalResult {
  chunk_id: string;
  score_vector: number;
  score_keyword: number;
  score_final: number;
  citation: Record<string, unknown>;
}

export interface QaResult {
  answer: string;
  citations: Citation[];
  confidence: number;
  refuse_reason: string | null;
  debug?: Record<string, unknown>;
}

export interface QaHistoryItem {
  qa_id: string;
  kb_id: string;
  question: string;
  answer: string;
  confidence: number;
  created_at: string;
}
