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
  section_path: string;
}

export interface Citation {
  chunk_id: string;
  citation: string;
  doc_id?: string;
  section_path?: string;
}

export interface RetrievalResult {
  chunk_id: string;
  score_vector: number;
  score_keyword: number;
  score_final: number;
  citation: string;
}

export interface QaResult {
  answer: string;
  citations: Citation[];
  confidence: number;
  refuse_reason: string | null;
}

export interface QaHistoryItem {
  qa_id: string;
  kb_id: string;
  question: string;
  answer: string;
  confidence: number;
  created_at: string;
}
