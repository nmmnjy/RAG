export type UploadState = "idle" | "uploading" | "uploaded" | "failed";
export type ParseState = "idle" | "parsing" | "parsed" | "failed";
export type IndexState = "idle" | "indexing" | "indexed" | "failed";
export type RetrieveState = "idle" | "retrieving" | "retrieved" | "empty" | "failed";
export type AnswerState = "idle" | "answering" | "answered" | "refused" | "failed";

export interface WorkflowState {
  upload_state: UploadState;
  parse_state: ParseState;
  index_state: IndexState;
  retrieve_state: RetrieveState;
  answer_state: AnswerState;
  error_code?: string;
  error_message?: string;
}

export interface StateNode {
  key: string;
  label: string;
  status: "todo" | "in_progress" | "success" | "warning" | "error";
}
