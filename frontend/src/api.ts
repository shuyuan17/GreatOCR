/// <reference types="vite/client" />

declare global {
  interface Window {
    __GREAT_OCR_TOKEN__: string
  }
}

const API_BASE = "/api"

/* ------------------------------------------------------------------ */
/*  Fetch wrapper                                                      */
/* ------------------------------------------------------------------ */

export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const headers = new Headers(init?.headers)
  const token = window.__GREAT_OCR_TOKEN__
  if (token) {
    headers.set("X-GreatOCR-Token", token)
  }
  return fetch(`${API_BASE}${path}`, { ...init, headers })
}

/* ------------------------------------------------------------------ */
/*  API 类型                                                           */
/* ------------------------------------------------------------------ */

export type TaskStatus =
  | "pending"
  | "running"
  | "paused"
  | "succeeded"
  | "partial"
  | "failed"
  | "cancelled"

export interface TaskRecord {
  task_id: string
  display_name: string
  source_path: string | null
  sensitive: boolean
  selected_pages: number[]
  provider_profile_id: string
  approved_fallback_ids: string[]
  status: TaskStatus
  output_dir: string
  quality_rating: string | null
  requested_action: string | null
  created_at: string
}

export interface UploadResult {
  task: TaskRecord
  file_path: string
  size_bytes: number
}

export interface ProviderView {
  profile_id: string
  display_name: string
  adapter_type: string
  endpoint: string | null
  public: boolean
  capabilities: Record<string, unknown>
  approved_fallback_ids: string[]
  credential: {
    configured: boolean
    masked: string | null
  }
}

/* ------------------------------------------------------------------ */
/*  Task API                                                           */
/* ------------------------------------------------------------------ */

/** 上传文件并创建任务 */
export async function uploadFile(
  file: File,
  opts?: {
    sensitive?: boolean
    providerProfileId?: string
  },
): Promise<UploadResult> {
  const form = new FormData()
  form.append("file", file)
  if (opts?.sensitive) form.append("sensitive", "true")
  if (opts?.providerProfileId)
    form.append("provider_profile_id", opts.providerProfileId)

  const res = await apiFetch("/tasks/upload-file", {
    method: "POST",
    body: form,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail?.code || `上传失败 (${res.status})`)
  }
  return res.json()
}

/** 获取单个任务详情 */
export async function getTask(taskId: string): Promise<TaskRecord> {
  const res = await apiFetch(`/tasks/${taskId}`)
  if (!res.ok) throw new Error(`获取任务失败 (${res.status})`)
  return res.json()
}

/** 启动任务（从 paused → pending） */
export async function startTask(taskId: string): Promise<TaskRecord> {
  const res = await apiFetch(`/tasks/${taskId}/start`, { method: "POST" })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err?.detail?.code || `启动失败 (${res.status})`)
  }
  return res.json()
}

/** 列出任务 */
export async function listTasks(): Promise<TaskRecord[]> {
  const res = await apiFetch("/tasks")
  if (!res.ok) throw new Error(`获取任务列表失败 (${res.status})`)
  return res.json()
}

/** 获取 Provider 列表 */
export async function listProviders(): Promise<ProviderView[]> {
  const res = await apiFetch("/providers")
  if (!res.ok) throw new Error(`获取 Provider 列表失败 (${res.status})`)
  return res.json()
}
