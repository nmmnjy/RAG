"use client";

import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { SectionBlock } from "@/components/layout/section-block";
import { askQuestion } from "@/features/qa/service";
import { buildWorkflowNodes } from "@/features/workflow/state-machine";
import { isApiError } from "@/lib/http";
import type { ApiErrorResponse, ApiSuccessResponse } from "@/types/api";
import type { QaResult } from "@/types/domain";
import type { WorkflowState } from "@/types/workflow";

type QaViewState = "idle" | "loading" | "answered" | "refused" | "failed";

const statusVariantMap = {
  todo: "default",
  in_progress: "warning",
  success: "success",
  warning: "warning",
  error: "danger"
} as const;

function normalizeInt(value: number, min: number, max: number): number {
  if (!Number.isFinite(value)) {
    return min;
  }
  return Math.min(max, Math.max(min, Math.floor(value)));
}

function buildQaWorkflowState(state: QaViewState): WorkflowState {
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

export default function QaPage(): React.JSX.Element {
  const [kbId, setKbId] = useState("kb_hr");
  const [queryText, setQueryText] = useState("");
  const [topK, setTopK] = useState(5);
  const [vectorTopK, setVectorTopK] = useState(20);
  const [keywordTopK, setKeywordTopK] = useState(20);
  const [enableRerank, setEnableRerank] = useState(false);
  const [qaState, setQaState] = useState<QaViewState>("idle");
  const [qaResult, setQaResult] = useState<QaResult | null>(null);
  const [apiMeta, setApiMeta] = useState<{ request_id: string; trace_id: string; ts?: string } | null>(null);
  const [errorInfo, setErrorInfo] = useState<ApiErrorResponse | null>(null);

  const nodes = useMemo(() => buildWorkflowNodes(buildQaWorkflowState(qaState)), [qaState]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    const cleaned = queryText.trim();
    if (!cleaned) {
      setQaState("failed");
      setQaResult(null);
      setErrorInfo({
        code: "COMMON_INVALID_ARGUMENT",
        message: "query_text is required",
        request_id: "req_frontend_validation",
        trace_id: "trace_frontend_validation"
      });
      return;
    }

    setQaState("loading");
    setErrorInfo(null);
    setQaResult(null);
    setApiMeta(null);

    const normalizedTopK = normalizeInt(topK, 1, 100);
    const normalizedVectorTopK = normalizeInt(vectorTopK, 1, 100);
    const normalizedKeywordTopK = normalizeInt(keywordTopK, 1, 100);

    const response = await askQuestion({
      kb_id: kbId.trim(),
      query_text: cleaned,
      top_k: normalizedTopK,
      vector_top_k: normalizedVectorTopK,
      keyword_top_k: normalizedKeywordTopK,
      enable_rerank: enableRerank
    });

    if (isApiError(response)) {
      setQaState("failed");
      setErrorInfo(response);
      setApiMeta({ request_id: response.request_id, trace_id: response.trace_id });
      return;
    }

    const successResponse: ApiSuccessResponse<QaResult> = response;
    setQaResult(successResponse.data);
    setApiMeta({
      request_id: successResponse.request_id,
      trace_id: successResponse.trace_id,
      ts: successResponse.ts
    });
    setQaState(successResponse.data.refuse_reason ? "refused" : "answered");
  };

  return (
    <div className="space-y-6">
      <SectionBlock title="用户问答" description="联调版本：可提交问题、展示结果、处理拒答和失败态。">
        <Card>
          <CardTitle>提问区</CardTitle>
          <CardDescription>请求字段使用 `kb_id/query_text/top_k/vector_top_k/keyword_top_k/enable_rerank`。</CardDescription>
          <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
            <div className="grid gap-3 md:grid-cols-4">
              <input
                className="h-10 rounded-lg border border-[var(--border)] bg-white px-3 text-sm outline-none focus:border-[var(--brand)]"
                placeholder="kb_id"
                value={kbId}
                onChange={(event) => setKbId(event.target.value)}
              />
              <input
                className="h-10 md:col-span-3 rounded-lg border border-[var(--border)] bg-white px-3 text-sm outline-none focus:border-[var(--brand)]"
                placeholder="请输入问题"
                value={queryText}
                onChange={(event) => setQueryText(event.target.value)}
              />
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <label className="text-sm text-[#4f5645]">
                top_k
                <input
                  type="number"
                  min={1}
                  max={100}
                  className="mt-1 h-10 w-full rounded-lg border border-[var(--border)] bg-white px-3 text-sm outline-none focus:border-[var(--brand)]"
                  value={topK}
                  onChange={(event) => setTopK(Number(event.target.value))}
                />
              </label>
              <label className="text-sm text-[#4f5645]">
                vector_top_k
                <input
                  type="number"
                  min={1}
                  max={100}
                  className="mt-1 h-10 w-full rounded-lg border border-[var(--border)] bg-white px-3 text-sm outline-none focus:border-[var(--brand)]"
                  value={vectorTopK}
                  onChange={(event) => setVectorTopK(Number(event.target.value))}
                />
              </label>
              <label className="text-sm text-[#4f5645]">
                keyword_top_k
                <input
                  type="number"
                  min={1}
                  max={100}
                  className="mt-1 h-10 w-full rounded-lg border border-[var(--border)] bg-white px-3 text-sm outline-none focus:border-[var(--brand)]"
                  value={keywordTopK}
                  onChange={(event) => setKeywordTopK(Number(event.target.value))}
                />
              </label>
              <label className="flex items-end gap-2 rounded-lg border border-[var(--border)] bg-white px-3 py-2 text-sm text-[#4f5645]">
                <input type="checkbox" checked={enableRerank} onChange={(event) => setEnableRerank(event.target.checked)} />
                enable_rerank
              </label>
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={qaState === "loading"}>
                {qaState === "loading" ? "问答中..." : "开始问答"}
              </Button>
              <Badge variant={qaState === "failed" ? "danger" : qaState === "refused" ? "warning" : qaState === "answered" ? "success" : "default"}>
                state: {qaState}
              </Badge>
            </div>
          </form>
        </Card>
      </SectionBlock>

      <SectionBlock title="状态流转" description="上传 -> 解析 -> 索引构建 -> 检索 -> 问答">
        <div className="grid gap-3 md:grid-cols-5">
          {nodes.map((node) => (
            <Card key={node.key} className="space-y-2 p-4">
              <CardTitle className="text-sm">{node.label}</CardTitle>
              <Badge variant={statusVariantMap[node.status]}>{node.status}</Badge>
            </Card>
          ))}
        </div>
      </SectionBlock>

      <SectionBlock title="答案与引用" description="字段遵循 PRD：answer/citations/confidence/refuse_reason">
        <Card>
          <CardTitle>答案</CardTitle>
          {qaState === "idle" ? <CardDescription>请输入问题后提交。</CardDescription> : null}
          {qaState === "loading" ? <CardDescription>正在执行检索与答案生成...</CardDescription> : null}
          {qaState === "failed" && errorInfo ? (
            <div className="space-y-2">
              <CardDescription className="text-[var(--danger)]">
                {errorInfo.code}: {errorInfo.message}
              </CardDescription>
              <p className="text-xs text-[#5a6151]">request_id={errorInfo.request_id} trace_id={errorInfo.trace_id}</p>
            </div>
          ) : null}
          {(qaState === "answered" || qaState === "refused") && qaResult ? (
            <div className="space-y-4">
              <CardDescription>{qaResult.answer}</CardDescription>
              <div className="flex flex-wrap items-center gap-3">
                <Badge variant={qaState === "refused" ? "warning" : "success"}>confidence: {qaResult.confidence}</Badge>
                {qaResult.refuse_reason ? <Badge variant="warning">refuse_reason: {qaResult.refuse_reason}</Badge> : null}
                <Badge variant="default">
                  top_k={topK} vector_top_k={vectorTopK} keyword_top_k={keywordTopK} rerank={enableRerank ? "on" : "off"}
                </Badge>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-medium">citations</h4>
                {qaResult.citations.length === 0 ? (
                  <p className="text-sm text-[#5a6151]">暂无引用（拒答或证据不足）。</p>
                ) : (
                  <ul className="space-y-2">
                    {qaResult.citations.map((item) => (
                      <li key={item.citation_id} className="rounded-lg bg-[var(--surface-muted)] p-3 text-sm">
                        <p className="font-medium">
                          {item.source ?? "-"} | {item.section_path.join(" / ")}
                        </p>
                        <p className="mt-1 text-[#4f5645]">{item.snippet}</p>
                        <p className="mt-1 text-xs text-[#5a6151]">
                          citation_id={item.citation_id} chunk_id={item.chunk_id} score_final={item.score_final}
                        </p>
                        <pre className="mt-1 overflow-x-auto text-xs text-[#5a6151]">{JSON.stringify(item.citation, null, 2)}</pre>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {qaResult.debug ? (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">debug</h4>
                  <pre className="overflow-x-auto rounded-lg bg-[var(--surface-muted)] p-3 text-xs text-[#5a6151]">
                    {JSON.stringify(qaResult.debug, null, 2)}
                  </pre>
                </div>
              ) : null}
              {apiMeta ? (
                <p className="text-xs text-[#5a6151]">
                  request_id={apiMeta.request_id} trace_id={apiMeta.trace_id} {apiMeta.ts ? `ts=${apiMeta.ts}` : ""}
                </p>
              ) : null}
            </div>
          ) : null}
        </Card>
      </SectionBlock>
    </div>
  );
}
