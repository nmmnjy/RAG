import type { ApiErrorResponse, ApiSuccessResponse } from "@/types/api";
import type { QaHistoryItem, QaResult } from "@/types/domain";
import type { WorkflowState } from "@/types/workflow";

export const demoQaState: WorkflowState = {
  upload_state: "uploaded",
  parse_state: "parsed",
  index_state: "indexed",
  retrieve_state: "retrieving",
  answer_state: "idle"
};

export const demoQaResult: QaResult = {
  answer: "这里是问答结果占位。后续联调后将展示真实答案与引用映射关系。",
  citations: [
    {
      citation_id: "cit_001",
      chunk_id: "chunk_001",
      doc_id: "doc_001",
      kb_id: "kb_hr",
      section_path: ["员工手册", "请假制度", "年假规则"],
      snippet: "员工年假申请需至少提前 3 个工作日提交，经直属主管审批后生效。",
      score_final: 0.81,
      source: "employee-handbook.pdf",
      citation: {
        source: "employee-handbook.pdf",
        section_path: ["员工手册", "请假制度", "年假规则"],
        note: "员工手册 > 请假制度 > 年假规则"
      }
    }
  ],
  confidence: 0.84,
  refuse_reason: null
};

export const demoHistory: QaHistoryItem[] = [
  {
    qa_id: "qa_001",
    kb_id: "kb_hr",
    question: "年假最少提前几天申请？",
    answer: "建议至少提前 3 个工作日提交申请。",
    confidence: 0.84,
    created_at: "2026-03-28T10:20:00+08:00"
  }
];

export const demoQaSuccessResponse: ApiSuccessResponse<QaResult> = {
  code: "OK",
  message: "success",
  data: demoQaResult,
  request_id: "req_qa_001",
  trace_id: "trace_qa_001",
  ts: "2026-03-28T10:20:00Z"
};

export const demoQaRefusedResponse: ApiSuccessResponse<QaResult> = {
  code: "OK",
  message: "success",
  data: {
    answer: "抱歉，我当前无法基于现有检索证据可靠回答这个问题。",
    citations: [],
    confidence: 0,
    refuse_reason: "QA_CONTEXT_EMPTY"
  },
  request_id: "req_qa_003",
  trace_id: "trace_qa_001",
  ts: "2026-03-28T10:21:00Z"
};

export const demoQaErrorResponse: ApiErrorResponse = {
  code: "QA_CONTEXT_EMPTY",
  message: "no context available for current question",
  details: { kb_id: "kb_hr" },
  request_id: "req_qa_002",
  trace_id: "trace_qa_001"
};
