export interface ApiSuccessResponse<T> {
  code: string;
  message: string;
  data: T;
  request_id: string;
  trace_id: string;
  ts: string;
}

export interface ApiErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  request_id: string;
  trace_id: string;
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;
