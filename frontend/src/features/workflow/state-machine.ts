import type { StateNode, WorkflowState } from "@/types/workflow";

function toNodeStatus(
  phaseState: "idle" | "uploading" | "uploaded" | "parsing" | "parsed" | "indexing" | "indexed" | "retrieving" | "retrieved" | "empty" | "answering" | "answered" | "refused" | "failed"
): StateNode["status"] {
  if (phaseState === "failed") {
    return "error";
  }
  if (phaseState === "empty" || phaseState === "refused") {
    return "warning";
  }
  if (phaseState.endsWith("ing")) {
    return "in_progress";
  }
  if (phaseState.endsWith("ed")) {
    return "success";
  }
  return "todo";
}

export function buildWorkflowNodes(state: WorkflowState): StateNode[] {
  return [
    { key: "upload", label: "上传", status: toNodeStatus(state.upload_state) },
    { key: "parse", label: "解析", status: toNodeStatus(state.parse_state) },
    { key: "index", label: "索引构建", status: toNodeStatus(state.index_state) },
    { key: "retrieve", label: "检索", status: toNodeStatus(state.retrieve_state) },
    { key: "answer", label: "问答", status: toNodeStatus(state.answer_state) }
  ];
}
