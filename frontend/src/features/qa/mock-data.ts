import type { ApiErrorResponse, ApiSuccessResponse } from "@/types/api";
import type { QaHistoryItem, QaResult } from "@/types/domain";
import type { WorkflowState } from "@/types/workflow";

type QaSuccessData = {
  result: QaResult;
  retrieval_results: {
    chunk_id: string;
    score_vector: number;
    score_keyword: number;
    score_final: number;
    citation: string;
  }[];
};

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
      chunk_id: "chunk_001",
      citation: "员工手册 > 请假制度 > 年假规则",
      doc_id: "doc_001",
      section_path: "员工手册/请假制度/年假规则"
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

export const demoQaSuccessResponse: ApiSuccessResponse<QaSuccessData> = {
  code: "OK",
  message: "success",
  data: {
    result: demoQaResult,
    retrieval_results: [
      {
        chunk_id: "chunk_001",
        score_vector: 0.82,
        score_keyword: 0.79,
        score_final: 0.81,
        citation: "员工手册 > 请假制度 > 年假规则"
      }
    ]
  },
  request_id: "req_qa_001",
  trace_id: "trace_qa_001",
  ts: "2026-03-28T10:20:00Z"
};

export const demoQaErrorResponse: ApiErrorResponse = {
  code: "QA_CONTEXT_EMPTY",
  message: "no context available for current question",
  details: { kb_id: "kb_hr" },
  request_id: "req_qa_002",
  trace_id: "trace_qa_001"
};
