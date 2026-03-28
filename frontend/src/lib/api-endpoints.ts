export const API_PREFIX = "/api/v1";

export const apiEndpoints = {
  qa: `${API_PREFIX}/qa/ask`,
  qa_history: `${API_PREFIX}/qa/history`,
  kbs: `${API_PREFIX}/kbs`,
  documents: `${API_PREFIX}/documents`,
  tasks: `${API_PREFIX}/tasks`,
  logs: `${API_PREFIX}/logs`
} as const;
