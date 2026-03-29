import type { WorkflowState } from "@/types/workflow";

export type QaViewState = "idle" | "loading" | "answered" | "refused" | "failed";

export function normalizeInt(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, Math.floor(value)));
}

export function buildQaWorkflowState(state: QaViewState): WorkflowState {
  if (state === "idle") {
    return {
      upload_state: "uploaded",
      parse_state: "parsed",
      index_state: "indexed",
      retrieve_state: "idle",
      answer_state: "idle"
    };
  }
  if (state === "loading") {
    return {
      upload_state: "uploaded",
      parse_state: "parsed",
      index_state: "indexed",
      retrieve_state: "retrieving",
      answer_state: "answering"
    };
  }
  if (state === "answered") {
    return {
      upload_state: "uploaded",
      parse_state: "parsed",
      index_state: "indexed",
      retrieve_state: "retrieved",
      answer_state: "answered"
    };
  }
  if (state === "refused") {
    return {
      upload_state: "uploaded",
      parse_state: "parsed",
      index_state: "indexed",
      retrieve_state: "empty",
      answer_state: "refused"
    };
  }
  return {
    upload_state: "uploaded",
    parse_state: "parsed",
    index_state: "indexed",
    retrieve_state: "failed",
    answer_state: "failed"
  };
}
