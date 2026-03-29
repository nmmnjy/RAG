import { describe, expect, it } from "vitest";

import { buildQaWorkflowState, normalizeInt } from "@/features/qa/qa-state";

describe("qa-state helpers", () => {
  it("normalizes integer bounds", () => {
    expect(normalizeInt(Number.NaN, 1, 100)).toBe(1);
    expect(normalizeInt(0, 1, 100)).toBe(1);
    expect(normalizeInt(150, 1, 100)).toBe(100);
    expect(normalizeInt(9.8, 1, 100)).toBe(9);
  });

  it("maps view state to workflow state", () => {
    expect(buildQaWorkflowState("loading")).toMatchObject({
      retrieve_state: "retrieving",
      answer_state: "answering"
    });
    expect(buildQaWorkflowState("refused")).toMatchObject({
      retrieve_state: "empty",
      answer_state: "refused"
    });
  });
});
