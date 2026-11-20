const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

export type Task = {
  id: string;
  title: string;
  description: string;
  repository_url: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type AgentRun = {
  id: string;
  task_id: string;
  thread_id: string;
  status: string;
  created_at: string;
  updated_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_URL) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  }

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = typeof window !== "undefined"
    ? localStorage.getItem("forgeai_access_token")
    : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : `API request failed (${response.status}).`);
  }
  return body as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  register: (email: string, password: string) =>
    request<{ access_token: string }>("/api/v1/auth/register", {
      method: "POST", body: JSON.stringify({ email, password }),
    }),
  listTasks: () => request<Task[]>("/api/v1/tasks"),
  getTask: (id: string) => request<Task>(`/api/v1/tasks/${id}`),
  createTask: (payload: { title: string; description: string; repository_url: string }) =>
    request<Task>("/api/v1/tasks", { method: "POST", body: JSON.stringify(payload) }),
  startRun: (taskId: string) =>
    request<AgentRun>(`/api/v1/tasks/${taskId}/runs`, { method: "POST" }),
  getRun: (runId: string) => request<AgentRun>(`/api/v1/runs/${runId}`),
  listRuns: (taskId: string) =>
    request<AgentRun[]>(`/api/v1/runs?task_id=${encodeURIComponent(taskId)}&limit=1`),
};
