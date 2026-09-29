const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export class ApiError extends Error {}

async function request<T>(path: string, token: string | null, options: RequestInit = {}): Promise<T> {
  const res = await fetch(API_BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return null as T;
  return res.json();
}

export const api = {
  base: API_BASE,

  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", null, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/register", null, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  listEmails: (token: string, search?: string) =>
    request<import("../types").EmailOut[]>(
      `/emails?page=1&page_size=100${search ? `&search=${encodeURIComponent(search)}` : ""}`,
      token
    ),

  getEmail: (token: string, id: string) => request<import("../types").EmailOut>(`/emails/${id}`, token),

  generateReplies: (token: string, id: string) =>
    request<import("../types").GenerateRepliesResponse>(`/emails/${id}/generate-replies`, token, {
      method: "POST",
    }),

  regenerateReply: (token: string, replyId: string) =>
    request<import("../types").ReplyOut>(`/replies/${replyId}/regenerate`, token, { method: "POST" }),

  modifyReply: (token: string, replyId: string, instruction: string) =>
    request<import("../types").ReplyOut>(`/replies/${replyId}/modify`, token, {
      method: "POST",
      body: JSON.stringify({ instruction }),
    }),

  sendReply: (token: string, emailId: string, replyId: string, accountId?: string) =>
    request<{ status: string }>(`/emails/${emailId}/send`, token, {
      method: "POST",
      body: JSON.stringify({ reply_id: replyId, account_id: accountId || null }),
    }),

  bulkProcess: (token: string, limit = 1000) =>
    request<import("../types").BulkJobOut>(`/emails/bulk-process`, token, {
      method: "POST",
      body: JSON.stringify({ limit }),
    }),

  bulkStatus: (token: string, jobId: string) =>
    request<import("../types").BulkJobOut>(`/emails/bulk-status/${jobId}`, token),

  bulkRetry: (token: string, jobId: string) =>
    request<import("../types").BulkJobOut>(`/emails/bulk-retry/${jobId}`, token, { method: "POST" }),

  googleConnectUrl: (token: string) => request<{ url: string }>(`/email/google/connect-url`, token),

  listAccounts: (token: string) => request<import("../types").EmailAccountOut[]>(`/email/accounts`, token),

  disconnectAccount: (token: string, id: string) =>
    request<null>(`/email/accounts/${id}`, token, { method: "DELETE" }),

  syncAccount: (token: string, id: string, limit = 50) =>
    request<import("../types").SyncResponse>(`/email/accounts/${id}/sync?limit=${limit}`, token, { method: "POST" }),

  analytics: (token: string) => request<import("../types").AnalyticsOut>(`/analytics`, token),
};
