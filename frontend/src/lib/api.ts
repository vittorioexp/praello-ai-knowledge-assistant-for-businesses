import { getAccessToken } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface DocumentResponse {
  id: string;
  original_filename: string;
  status: string;
  chunk_count: number;
  document_type: string;
  created_at: string;
}

export interface RAGResponse {
  answer: string;
  confidence: number;
  sources: Array<{
    document_name: string;
    excerpt: string;
    relevance_score: number;
  }>;
  retrieval_count: number;
}

export interface AgentResponse {
  thread_id: string;
  status: string;
  answer: string;
  confidence: number;
  requires_approval: boolean;
  tool_results: Array<{ tool_name: string; output: string }>;
}

export interface LLMModelUsage {
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

export interface LLMUsageResponse {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  cache_hits: number;
  by_model: Record<string, LLMModelUsage>;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getAccessToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, password: string, full_name: string) =>
    request<UserResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  me: () => request<UserResponse>("/auth/me"),

  listDocuments: () =>
    request<{ items: DocumentResponse[] }>("/documents"),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentResponse>("/documents/upload", {
      method: "POST",
      body: form,
      headers: {},
    });
  },

  queryKnowledge: (query: string) =>
    request<RAGResponse>("/knowledge/query", {
      method: "POST",
      body: JSON.stringify({ query, use_multi_query: true, use_reranking: true }),
    }),

  agentChat: (message: string, threadId?: string) =>
    request<AgentResponse>("/agent/conversations", {
      method: "POST",
      body: JSON.stringify({ message, thread_id: threadId || null }),
    }),

  approveAction: (threadId: string, approved = true) =>
    request<AgentResponse>(`/agent/conversations/${threadId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved }),
    }),

  llmUsage: () => request<LLMUsageResponse>("/llm/usage"),
};
