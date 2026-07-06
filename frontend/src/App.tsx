import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react"
import { Link, Route, Routes, useNavigate, useSearchParams } from "react-router-dom"
import {
  apiFetch,
  batchDeleteTasks,
  deleteTask,
  getDefaultOutputDir,
  getPreferences,
  getTask,
  getTaskResultFiles,
  listProviders,
  listTasks,
  openOutput,
  startTask,
  testProviderConnection,
  updatePreferences,
  updateProviderCredential,
  updateProviderProfile,
  uploadFile,
  type Preferences,
  type ProviderView,
  type TaskRecord,
  type TaskResultSummary,
  type TaskStatus,
} from "./api"
import { isPdfFile, validatePageRange } from "./pageRanges"
import {
  AI_PROCESSING_MODES,
  AI_PROVIDER_CATALOG,
  DEFAULT_AI_MODE,
  DEFAULT_OCR_PROVIDER,
  DEFAULT_SENSITIVE,
  DEFAULT_TRANSLATION_PROVIDER,
  DEFAULT_TARGET_LANGUAGE,
  DEFAULT_TRANSLATION_MODE,
  SENSITIVE_OPTIONS,
  TARGET_LANGUAGES,
  TRANSLATION_MODES,
  type AiModeValue,
  type SensitiveValue,
  type TargetLanguage,
  type TranslationMode,
} from "./aiProcessing"

type HealthState = "loading" | "ok" | "error"

const STATUS_LABELS: Record<TaskStatus, string> = {
  pending: "等待处理",
  running: "处理中",
  paused: "已暂停",
  succeeded: "已完成",
  partial: "部分完成",
  failed: "失败",
  cancelled: "已取消",
}

const STATUS_COLORS: Record<TaskStatus, string> = {
  pending: "#856404",
  running: "#1565c0",
  paused: "#6a1b9a",
  succeeded: "#2e7d32",
  partial: "#e65100",
  failed: "#c62828",
  cancelled: "#9e9e9e",
}

const TERMINAL_STATUSES: TaskStatus[] = ["succeeded", "partial", "failed", "cancelled"]

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatPages(pages: number[]): string {
  if (pages.length === 0) return "全部页面"
  if (pages.length === 1) return `第 ${pages[0]} 页`
  return pages.join(", ")
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function canViewResults(status: TaskStatus): boolean {
  return TERMINAL_STATUSES.includes(status)
}

function HealthBadge() {
  const [state, setState] = useState<HealthState>("loading")
  const [label, setLabel] = useState("正在连接后端...")

  useEffect(() => {
    let cancelled = false
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    const check = async () => {
      try {
        const res = await apiFetch("/health")
        if (!res.ok) {
          if (!cancelled) {
            setState("error")
            setLabel(`后端错误 (${res.status})`)
          }
          return
        }
        const data: { status: string } = await res.json()
        if (!cancelled) {
          if (data.status === "ok") {
            setState("ok")
            setLabel("后端已连接")
          } else {
            setState("error")
            setLabel(`后端异常: ${data.status}`)
          }
        }
      } catch {
        if (!cancelled) {
          setState("error")
          setLabel("无法连接后端")
        }
      }
    }

    check()

    return () => {
      cancelled = true
      if (retryTimer) clearTimeout(retryTimer)
    }
  }, [])

  const handleRetry = () => {
    setState("loading")
    setLabel("正在重试连接...")
    // 通过短暂延迟再检查，让用户看到重试状态
    setTimeout(() => {
      apiFetch("/health")
        .then(async (res) => {
          if (res.ok) {
            const data: { status: string } = await res.json()
            if (data.status === "ok") {
              setState("ok")
              setLabel("后端已连接")
            } else {
              setState("error")
              setLabel(`后端异常: ${data.status}`)
            }
          } else {
            setState("error")
            setLabel(`后端错误 (${res.status})`)
          }
        })
        .catch(() => {
          setState("error")
          setLabel("无法连接后端")
        })
    }, 500)
  }

  const indicator = state === "loading" ? "⏳" : state === "ok" ? "✅" : "❌"

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <span
        style={{
          fontSize: "0.8rem",
          padding: "2px 10px",
          borderRadius: 12,
          background: state === "ok" ? "#e6f7e6" : state === "error" ? "#fde8e8" : "#fff3cd",
          color: state === "ok" ? "#2e7d32" : state === "error" ? "#c62828" : "#856404",
          border: `1px solid ${
            state === "ok" ? "#a5d6a7" : state === "error" ? "#ef9a9a" : "#ffe082"
          }`,
          display: "inline-flex",
          alignItems: "center",
          gap: 4,
        }}
      >
        {indicator} {label}
      </span>
      {state === "error" && (
        <button
          onClick={handleRetry}
          title="重试连接后端"
          style={{
            fontSize: "0.75rem",
            padding: "2px 10px",
            color: "#1565c0",
            background: "#e3f2fd",
            border: "1px solid #90caf9",
            borderRadius: 12,
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          重试
        </button>
      )}
      {state === "error" && (
        <span
          style={{ fontSize: "0.75rem", color: "#888", cursor: "default" }}
          title="确保后端已启动（在终端运行 serve.py）"
        >
          ⓘ
        </span>
      )}
    </div>
  )
}

function NewTaskPage() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [providers, setProviders] = useState<ProviderView[]>([])
  const [selectedProvider, setSelectedProvider] = useState("")
  const [pageRange, setPageRange] = useState("")
  const [sensitive, setSensitive] = useState<SensitiveValue>(DEFAULT_SENSITIVE)
  const [aiMode, setAiMode] = useState<AiModeValue>(DEFAULT_AI_MODE)
  const [targetLanguage, setTargetLanguage] = useState<TargetLanguage>(
    DEFAULT_TARGET_LANGUAGE,
  )
  const [translationMode, setTranslationMode] = useState<TranslationMode>(
    DEFAULT_TRANSLATION_MODE,
  )
  const [outputDir, setOutputDir] = useState("")
  const [phase, setPhase] = useState<
    "idle" | "uploading" | "starting" | "running" | "done" | "error"
  >("idle")
  const [task, setTask] = useState<TaskRecord | null>(null)
  const [errorMsg, setErrorMsg] = useState("")
  const [progressMsg, setProgressMsg] = useState("")
  const pageRangeError = validatePageRange(pageRange)
  const pdfSelected = isPdfFile(file)

  useEffect(() => {
    listProviders()
      .then((list) => {
        setProviders(list)
        if (list.length > 0) {
          setSelectedProvider(list[0].profile_id)
        }
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    getDefaultOutputDir()
      .then((result) => setOutputDir(result.output_dir))
      .catch(() => {})
  }, [])

  const pollTask = useCallback(async (taskId: string) => {
    const maxAttempts = 120
    for (let i = 0; i < maxAttempts; i += 1) {
      try {
        const nextTask = await getTask(taskId)
        setTask(nextTask)
        setProgressMsg(STATUS_LABELS[nextTask.status])

        if (TERMINAL_STATUSES.includes(nextTask.status)) {
          setPhase("done")
          return nextTask
        }
        if (nextTask.status === "running") {
          setPhase("running")
        }
      } catch {
        // Continue polling.
      }
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }
    setPhase("error")
    setErrorMsg("轮询超时，请刷新页面后在任务中心查看结果。")
    return null
  }, [])

  const handleSubmit = async () => {
    if (!file) return
    if (pageRange.trim() && !pdfSelected) {
      setErrorMsg("只有 PDF 支持页码范围")
      return
    }
    if (pageRangeError) {
      setErrorMsg(pageRangeError)
      return
    }

    setPhase("uploading")
    setErrorMsg("")
    setProgressMsg("正在上传文件...")

    try {
      const uploaded = await uploadFile(file, {
        providerProfileId: selectedProvider,
        pages: pdfSelected ? pageRange : "",
        outputDir,
      })
      setTask(uploaded.task)
      setProgressMsg("文件已上传，正在启动 OCR...")

      setPhase("starting")
      const started = await startTask(uploaded.task.task_id)
      setTask(started)

      setPhase("running")
      setProgressMsg("任务已加入队列，等待处理...")
      const finalTask = await pollTask(uploaded.task.task_id)
      if (finalTask) {
        navigate(`/tasks?task=${finalTask.task_id}`)
      }
    } catch (err: unknown) {
      setPhase("error")
      setErrorMsg(err instanceof Error ? err.message : "操作失败")
    }
  }

  const providerReady = !!providers.find(
    (provider) => provider.profile_id === selectedProvider,
  )?.credential?.configured

  const currentMode =
    AI_PROCESSING_MODES.find((mode) => mode.value === aiMode) ??
    AI_PROCESSING_MODES[0]

  const statusStyle: CSSProperties = {
    marginTop: 16,
    padding: "12px 16px",
    borderRadius: 8,
    fontSize: "0.95rem",
    lineHeight: 1.6,
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 640, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0, color: "#333" }}>AI Processing</h2>
      <div style={{ marginBottom: 16, fontSize: "0.9rem", color: "#666" }}>
        OCR + AI 后处理工作流
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          htmlFor="source-file"
          style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}
        >
          选择文件（图片或 PDF）
        </label>
        <input
          id="source-file"
          aria-label="选择文件"
          ref={fileRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp"
          disabled={phase !== "idle"}
          onChange={(event) => {
            const nextFile = event.target.files?.[0] ?? null
            setFile(nextFile)
            setErrorMsg("")
            if (!isPdfFile(nextFile)) {
              setPageRange("")
            }
          }}
          style={{ fontSize: "0.95rem" }}
        />
        {file && (
          <div style={{ marginTop: 6, fontSize: "0.85rem", color: "#666" }}>
            {file.name} ({formatSize(file.size)})
          </div>
        )}
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          htmlFor="page-range"
          style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}
        >
          页码范围
        </label>
        <input
          id="page-range"
          aria-label="页码范围"
          type="text"
          value={pageRange}
          disabled={phase !== "idle" || !pdfSelected}
          onChange={(event) => {
            setPageRange(event.target.value)
            setErrorMsg("")
          }}
          placeholder="留空处理全部页面，例如：1-3,5,7-9"
          style={{
            width: "100%",
            fontSize: "0.95rem",
            padding: "8px 10px",
            boxSizing: "border-box",
          }}
        />
        <div
          style={{
            marginTop: 6,
            fontSize: "0.8rem",
            color: pageRangeError ? "#c62828" : "#666",
          }}
        >
          {pageRangeError ||
            (pdfSelected
              ? "支持 1、1-3、1,3,5、1-3,5,7-9；留空表示全部页面"
              : "仅 PDF 支持页码范围")}
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          htmlFor="sensitive-select"
          style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}
        >
          是否敏感文件？
        </label>
        <select
          id="sensitive-select"
          aria-label="是否敏感文件"
          value={sensitive}
          disabled={phase !== "idle"}
          onChange={(event) => setSensitive(event.target.value as SensitiveValue)}
          style={{ fontSize: "0.95rem", padding: "4px 8px" }}
        >
          {SENSITIVE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <div style={{ marginTop: 6, fontSize: "0.8rem", color: "#666" }}>
          敏感文件会限制可用 Provider，避免发送到不合适的外部服务。
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          htmlFor="ai-mode-select"
          style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}
        >
          AI Processing Mode
        </label>
        <select
          id="ai-mode-select"
          aria-label="AI Processing Mode"
          value={aiMode}
          disabled={phase !== "idle"}
          onChange={(event) => setAiMode(event.target.value as AiModeValue)}
          style={{ fontSize: "0.95rem", padding: "4px 8px" }}
        >
          {AI_PROCESSING_MODES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <div style={{ marginTop: 6, fontSize: "0.8rem", color: "#666" }}>
          {currentMode.description}
        </div>
        {aiMode === "translation" && (
          <div
            style={{
              marginTop: 12,
              paddingLeft: 12,
              borderLeft: "3px solid #e0e0e0",
            }}
          >
            <div style={{ marginBottom: 16 }}>
              <label
                htmlFor="target-language-select"
                style={{
                  display: "block",
                  marginBottom: 6,
                  fontWeight: 500,
                  color: "#555",
                }}
              >
                Target Language
              </label>
              <select
                id="target-language-select"
                aria-label="Target Language"
                value={targetLanguage}
                disabled={phase !== "idle"}
                onChange={(event) =>
                  setTargetLanguage(event.target.value as TargetLanguage)
                }
                style={{ fontSize: "0.95rem", padding: "4px 8px" }}
              >
                {TARGET_LANGUAGES.map((language) => (
                  <option key={language} value={language}>
                    {language}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label
                htmlFor="translation-mode-select"
                style={{
                  display: "block",
                  marginBottom: 6,
                  fontWeight: 500,
                  color: "#555",
                }}
              >
                Translation Mode
              </label>
              <select
                id="translation-mode-select"
                aria-label="Translation Mode"
                value={translationMode}
                disabled={phase !== "idle"}
                onChange={(event) =>
                  setTranslationMode(event.target.value as TranslationMode)
                }
                style={{ fontSize: "0.95rem", padding: "4px 8px" }}
              >
                {TRANSLATION_MODES.map((mode) => (
                  <option key={mode} value={mode}>
                    {mode}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ marginTop: 6, fontSize: "0.8rem", color: "#666" }}>
              Page by Page 会使用 OCR 时选择的页码范围，不需要用户重新输入页码。如果 OCR
              页码范围为空，则翻译全部 OCR 结果。
            </div>
          </div>
        )}
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 6, fontWeight: 500, color: "#555" }}>
          Current Workflow
        </div>
        <div style={{ fontSize: "0.95rem", color: "#333", marginBottom: 4 }}>
          OCR Provider: {DEFAULT_OCR_PROVIDER}
        </div>
        <div style={{ fontSize: "0.95rem", color: "#333" }}>
          Translation Provider:{" "}
          {aiMode === "translation" ? DEFAULT_TRANSLATION_PROVIDER : "Not used"}
        </div>
        <div style={{ marginTop: 4, fontSize: "0.8rem", color: "#666" }}>
          Providers are configured in <Link to="/settings">Settings</Link>.
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          htmlFor="output-dir"
          style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}
        >
          输出路径
        </label>
        <input
          id="output-dir"
          aria-label="输出路径"
          type="text"
          value={outputDir}
          disabled={phase !== "idle"}
          onChange={(event) => setOutputDir(event.target.value)}
          placeholder="默认输出到 data/exports，也可以手动填写自定义目录"
          style={{
            width: "100%",
            fontSize: "0.95rem",
            padding: "8px 10px",
            boxSizing: "border-box",
          }}
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={!file || !selectedProvider || phase !== "idle" || !providerReady}
        style={{
          padding: "10px 28px",
          fontSize: "1rem",
          fontWeight: 600,
          color: "#fff",
          background: phase !== "idle" ? "#9e9e9e" : "#1565c0",
          border: "none",
          borderRadius: 6,
          cursor: phase !== "idle" ? "not-allowed" : "pointer",
        }}
      >
        {phase === "idle"
          ? aiMode === "translation"
            ? "开始 OCR + 翻译"
            : "开始 OCR"
          : phase === "uploading"
            ? "上传中..."
            : phase === "starting"
              ? "启动中..."
              : phase === "running"
                ? "OCR 处理中..."
                : "完成"}
      </button>

      {phase !== "idle" && (
        <div
          style={{
            ...statusStyle,
            background:
              phase === "error"
                ? "#fde8e8"
                : phase === "done" && task?.status === "succeeded"
                  ? "#e6f7e6"
                  : "#e3f2fd",
            color:
              phase === "error"
                ? "#c62828"
                : phase === "done" && task?.status === "succeeded"
                  ? "#2e7d32"
                  : "#1565c0",
          }}
        >
          <div>
            <strong>状态：</strong>
            {progressMsg}
          </div>
          {task && (
            <>
              <div>
                <strong>任务 ID：</strong>
                <code style={{ fontSize: "0.85rem" }}>{task.task_id}</code>
              </div>
              <div>
                <strong>文件名：</strong>
                {task.display_name}
              </div>
              {task.status !== "running" && task.status !== "pending" && (
                <div>
                  <strong>输出目录：</strong>
                  <code style={{ fontSize: "0.85rem" }}>{task.output_dir}</code>
                </div>
              )}
              {task.quality_rating && (
                <div>
                  <strong>质量评分：</strong>
                  {task.quality_rating}
                </div>
              )}
            </>
          )}
          {errorMsg && <div style={{ marginTop: 8, color: "#c62828" }}>❌ {errorMsg}</div>}
        </div>
      )}

      {phase === "done" && task && (
        <div style={{ marginTop: 16 }}>
          <button
            onClick={() => navigate(`/tasks?task=${task.task_id}`)}
            style={{
              padding: "8px 20px",
              fontSize: "0.95rem",
              color: "#1565c0",
              background: "#e3f2fd",
              border: "1px solid #90caf9",
              borderRadius: 6,
              cursor: "pointer",
            }}
          >
            查看当前任务结果
          </button>
        </div>
      )}
    </div>
  )
}

function TaskCenterPage() {
  const [searchParams] = useSearchParams()
  const focusTaskId = searchParams.get("task")
  const [tasks, setTasks] = useState<TaskRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [resultSummaries, setResultSummaries] = useState<Record<string, TaskResultSummary>>({})
  const [resultLoading, setResultLoading] = useState<Record<string, boolean>>({})
  const [resultErrors, setResultErrors] = useState<Record<string, string>>({})
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [batchDeleteConfirm, setBatchDeleteConfirm] = useState(false)

  const PAGE_SIZE = 10

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const list = await listTasks()
        if (!cancelled) {
          setTasks(
            [...list].sort(
              (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
            ),
          )
        }
      } catch {
        if (!cancelled) {
          setTasks([])
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    load()
    const timer = setInterval(load, 5000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  // 重置页码当任务列表变化
  useEffect(() => {
    setPage(1)
    setSelectedIds(new Set())
  }, [tasks.length])

  // 为所有终止状态的任务加载结果文件信息（懒加载、只加载一次）
  useEffect(() => {
    const terminalTasks = tasks.filter((t) => TERMINAL_STATUSES.includes(t.status))
    const taskIdsToLoad = terminalTasks
      .map((t) => t.task_id)
      .filter((id) => !resultSummaries[id] && !resultLoading[id] && !resultErrors[id])

    if (taskIdsToLoad.length === 0) return

    taskIdsToLoad.forEach((taskId) => {
      setResultLoading((current) => ({ ...current, [taskId]: true }))
      getTaskResultFiles(taskId)
        .then((summary) => {
          setResultSummaries((current) => ({ ...current, [taskId]: summary }))
        })
        .catch(() => {
          setResultErrors((current) => ({
            ...current,
            [taskId]: "结果信息暂时无法读取",
          }))
        })
        .finally(() => {
          setResultLoading((current) => ({ ...current, [taskId]: false }))
        })
    })
  }, [tasks, resultErrors, resultLoading, resultSummaries])

  // 分页计算
  const totalPages = Math.max(1, Math.ceil(tasks.length / PAGE_SIZE))
  const safePage = Math.min(page, totalPages)
  const pageTasks = tasks.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE)

  // 选择状态计算
  const currentPageTerminal = pageTasks.filter((t) => TERMINAL_STATUSES.includes(t.status))
  const selectedCount = selectedIds.size
  const selectAllState: "all" | "some" | "none" =
    currentPageTerminal.length > 0 && currentPageTerminal.every((t) => selectedIds.has(t.task_id))
      ? "all"
      : currentPageTerminal.some((t) => selectedIds.has(t.task_id))
        ? "some"
        : "none"

  function handleSelectAll() {
    if (selectAllState === "all") {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(currentPageTerminal.map((t) => t.task_id)))
    }
  }

  function handleSelect(taskId: string) {
    setSelectedIds((current) => {
      const next = new Set(current)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const handleCopyPath = async (path: string) => {
    try {
      await navigator.clipboard.writeText(path)
      setCopyFeedback(path)
      setTimeout(() => setCopyFeedback(null), 2000)
    } catch {
      alert("复制失败，请手动复制。")
    }
  }

  const handleOpenOutput = async (taskId: string) => {
    try {
      await openOutput(taskId)
    } catch {
      alert("打开输出文件夹失败，请检查输出目录是否存在。")
    }
  }

  const handleDelete = async (taskId: string) => {
    try {
      await deleteTask(taskId)
      setTasks((current) => current.filter((t) => t.task_id !== taskId))
      setResultSummaries((current) => {
        const next = { ...current }
        delete next[taskId]
        return next
      })
    } catch {
      alert("删除任务失败，请稍后重试。")
    } finally {
      setDeleteConfirmId(null)
    }
  }

  const handleBatchDelete = async () => {
    const ids = [...selectedIds]
    try {
      await batchDeleteTasks(ids)
      setTasks((current) => current.filter((t) => !ids.includes(t.task_id)))
      setResultSummaries((current) => {
        const next = { ...current }
        ids.forEach((id) => delete next[id])
        return next
      })
      setSelectedIds(new Set())
    } catch {
      alert("批量删除失败，请稍后重试。")
    } finally {
      setBatchDeleteConfirm(false)
    }
  }

  // 表格列样式
  const thStyle: CSSProperties = {
    padding: "8px 10px",
    textAlign: "left",
    fontWeight: 600,
    fontSize: "0.85rem",
    color: "#555",
    borderBottom: "2px solid #e0e0e0",
    whiteSpace: "nowrap",
  }
  const tdStyle: CSSProperties = {
    padding: "8px 10px",
    fontSize: "0.85rem",
    color: "#333",
    borderBottom: "1px solid #eee",
    verticalAlign: "middle",
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 1200, margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h2 style={{ margin: 0, color: "#333" }}>任务中心</h2>
        {selectedCount > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: "0.85rem", color: "#666" }}>已选 {selectedCount} 项</span>
            <button
              onClick={() => setBatchDeleteConfirm(true)}
              style={{
                padding: "6px 16px",
                fontSize: "0.9rem",
                color: "#fff",
                background: "#c62828",
                border: "none",
                borderRadius: 6,
                cursor: "pointer",
              }}
            >
              删除选中
            </button>
          </div>
        )}
      </div>

      {loading && <div style={{ color: "#888", padding: "2rem 0" }}>加载中...</div>}

      {!loading && tasks.length === 0 && (
        <div style={{ color: "#888", padding: "2rem 0", textAlign: "center" }}>
          暂无任务，请前往“新建任务”开始。
        </div>
      )}

      {!loading && tasks.length > 0 && (
        <>
          {/* 批量删除确认弹窗 */}
          {batchDeleteConfirm && (
            <div
              style={{
                marginBottom: 16,
                padding: "12px 16px",
                borderRadius: 8,
                background: "#fff3cd",
                border: "1px solid #ffe082",
                fontSize: "0.9rem",
                color: "#856404",
              }}
            >
              <div style={{ marginBottom: 8 }}>
                ⚠️ 确认删除选中的 {selectedCount} 条任务记录？仅删除记录，不会删除输出文件。
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  onClick={handleBatchDelete}
                  style={{
                    padding: "6px 16px",
                    fontSize: "0.9rem",
                    color: "#fff",
                    background: "#c62828",
                    border: "none",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                >
                  确认删除
                </button>
                <button
                  onClick={() => setBatchDeleteConfirm(false)}
                  style={{
                    padding: "6px 16px",
                    fontSize: "0.9rem",
                    color: "#333",
                    background: "#fff",
                    border: "1px solid #ccc",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                >
                  取消
                </button>
              </div>
            </div>
          )}

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 900 }}>
              <thead>
                <tr style={{ background: "#fafafa" }}>
                  <th style={{ ...thStyle, width: 36, textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={selectAllState === "all"}
                      ref={(el) => {
                        if (el) el.indeterminate = selectAllState === "some"
                      }}
                      onChange={handleSelectAll}
                      aria-label="全选"
                    />
                  </th>
                  <th style={thStyle}>文件名</th>
                  <th style={{ ...thStyle, width: 90 }}>页码范围</th>
                  <th style={{ ...thStyle, width: 80 }}>状态</th>
                  <th style={{ ...thStyle, width: 140 }}>创建时间</th>
                  <th style={{ ...thStyle, width: 140 }}>完成时间</th>
                  <th style={thStyle}>输出目录</th>
                  <th style={{ ...thStyle, width: 160 }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {pageTasks.map((task) => {
                  const summary = resultSummaries[task.task_id]
                  const isResultLoading = !!resultLoading[task.task_id]
                  const isTerminal = TERMINAL_STATUSES.includes(task.status)

                  return (
                    <tr
                      key={task.task_id}
                      style={{
                        background: focusTaskId === task.task_id ? "#f6fbff" : undefined,
                      }}
                    >
                      {/* 选择框 */}
                      <td style={{ ...tdStyle, textAlign: "center" }}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(task.task_id)}
                          disabled={!isTerminal}
                          onChange={() => handleSelect(task.task_id)}
                          aria-label={`选择任务 ${task.display_name}`}
                        />
                      </td>

                      {/* 文件名 */}
                      <td style={tdStyle}>
                        <span style={{ fontWeight: 500 }}>{task.display_name}</span>
                      </td>

                      {/* 页码范围 */}
                      <td style={tdStyle}>
                        {formatPages(task.selected_pages)}
                      </td>

                      {/* 状态 */}
                      <td style={tdStyle}>
                        <span
                          style={{
                            fontSize: "0.8rem",
                            padding: "2px 8px",
                            borderRadius: 10,
                            background: `${STATUS_COLORS[task.status]}18`,
                            color: STATUS_COLORS[task.status],
                            border: `1px solid ${STATUS_COLORS[task.status]}40`,
                            whiteSpace: "nowrap",
                          }}
                        >
                          {STATUS_LABELS[task.status]}
                        </span>
                      </td>

                      {/* 创建时间 */}
                      <td style={tdStyle}>{formatDateTime(task.created_at)}</td>

                      {/* 完成时间 */}
                      <td style={tdStyle}>
                        {task.completed_at ? formatDateTime(task.completed_at) : "-"}
                      </td>

                      {/* 输出目录 */}
                      <td style={{ ...tdStyle, maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis" }}>
                        <code style={{ fontSize: "0.8rem" }}>
                          {task.output_dir.length > 30
                            ? `...${task.output_dir.slice(-30)}`
                            : task.output_dir}
                        </code>
                      </td>

                      {/* 操作 */}
                      <td style={tdStyle}>
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          <button
                            onClick={() => handleOpenOutput(task.task_id)}
                            title="打开输出文件夹"
                            style={{
                              padding: "2px 8px",
                              fontSize: "0.8rem",
                              color: "#1565c0",
                              background: "#e3f2fd",
                              border: "1px solid #90caf9",
                              borderRadius: 4,
                              cursor: "pointer",
                            }}
                          >
                            📁
                          </button>
                          <button
                            onClick={() => handleCopyPath(task.output_dir)}
                            title="复制输出路径"
                            style={{
                              padding: "2px 8px",
                              fontSize: "0.8rem",
                              color: copyFeedback === task.output_dir ? "#2e7d32" : "#1565c0",
                              background: copyFeedback === task.output_dir ? "#e6f7e6" : "#e3f2fd",
                              border: `1px solid ${copyFeedback === task.output_dir ? "#a5d6a7" : "#90caf9"}`,
                              borderRadius: 4,
                              cursor: "pointer",
                            }}
                          >
                            {copyFeedback === task.output_dir ? "✔" : "📋"}
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(task.task_id)}
                            title="删除任务"
                            style={{
                              padding: "2px 8px",
                              fontSize: "0.8rem",
                              color: "#c62828",
                              background: "#fde8e8",
                              border: "1px solid #ef9a9a",
                              borderRadius: 4,
                              cursor: "pointer",
                            }}
                          >
                            🗑
                          </button>
                          {/* 下载链接（以降级方式显示） */}
                          {isTerminal && (
                            <div style={{ display: "inline-flex", gap: 2, alignItems: "center" }}>
                              {isResultLoading && (
                                <span style={{ fontSize: "0.75rem", color: "#999" }}>加载中</span>
                              )}
                              {summary?.files.result_docx.exists && summary.files.result_docx.download_path ? (
                                <a
                                  href={summary.files.result_docx.download_path}
                                  style={{
                                    fontSize: "0.85rem",
                                    color: "#1565c0",
                                    textDecoration: "underline",
                                    padding: "0 4px",
                                  }}
                                  title="下载 result.docx"
                                >
                                  结果
                                </a>
                              ) : summary?.files.result_docx.exists ? (
                                <span
                                  style={{
                                    fontSize: "0.8rem",
                                    color: "#999",
                                    padding: "0 4px",
                                  }}
                                  title="文件暂不可下载"
                                >
                                  结果
                                </span>
                              ) : null}
                              {summary?.files.quality_report_docx.exists && summary.files.quality_report_docx.download_path ? (
                                <a
                                  href={summary.files.quality_report_docx.download_path}
                                  style={{
                                    fontSize: "0.85rem",
                                    color: "#1565c0",
                                    textDecoration: "underline",
                                    padding: "0 4px",
                                  }}
                                  title="下载 quality-report.docx"
                                >
                                  报告
                                </a>
                              ) : summary?.files.quality_report_docx.exists ? (
                                <span
                                  style={{
                                    fontSize: "0.8rem",
                                    color: "#999",
                                    padding: "0 4px",
                                  }}
                                  title="文件暂不可下载"
                                >
                                  报告
                                </span>
                              ) : null}
                            </div>
                          )}
                        </div>

                        {/* 单个删除确认 */}
                        {deleteConfirmId === task.task_id && (
                          <div
                            style={{
                              marginTop: 6,
                              padding: "8px 12px",
                              borderRadius: 6,
                              background: "#fff3cd",
                              border: "1px solid #ffe082",
                              fontSize: "0.8rem",
                              color: "#856404",
                            }}
                          >
                            <div style={{ marginBottom: 6 }}>
                              仅删除记录，不删除输出文件。
                            </div>
                            <div style={{ display: "flex", gap: 6 }}>
                              <button
                                onClick={() => handleDelete(task.task_id)}
                                style={{
                                  padding: "4px 12px",
                                  fontSize: "0.8rem",
                                  color: "#fff",
                                  background: "#c62828",
                                  border: "none",
                                  borderRadius: 4,
                                  cursor: "pointer",
                                }}
                              >
                                确认
                              </button>
                              <button
                                onClick={() => setDeleteConfirmId(null)}
                                style={{
                                  padding: "4px 12px",
                                  fontSize: "0.8rem",
                                  color: "#333",
                                  background: "#fff",
                                  border: "1px solid #ccc",
                                  borderRadius: 4,
                                  cursor: "pointer",
                                }}
                              >
                                取消
                              </button>
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: 16,
              marginTop: 20,
              fontSize: "0.9rem",
              color: "#666",
            }}
          >
            <button
              disabled={safePage <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              style={{
                padding: "6px 16px",
                fontSize: "0.9rem",
                color: safePage <= 1 ? "#ccc" : "#1565c0",
                background: safePage <= 1 ? "#f5f5f5" : "#e3f2fd",
                border: `1px solid ${safePage <= 1 ? "#e0e0e0" : "#90caf9"}`,
                borderRadius: 6,
                cursor: safePage <= 1 ? "not-allowed" : "pointer",
              }}
            >
              ← 上一页
            </button>
            <span>
              第 {safePage}/{totalPages} 页（共 {tasks.length} 条）
            </span>
            <button
              disabled={safePage >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              style={{
                padding: "6px 16px",
                fontSize: "0.9rem",
                color: safePage >= totalPages ? "#ccc" : "#1565c0",
                background: safePage >= totalPages ? "#f5f5f5" : "#e3f2fd",
                border: `1px solid ${safePage >= totalPages ? "#e0e0e0" : "#90caf9"}`,
                borderRadius: 6,
                cursor: safePage >= totalPages ? "not-allowed" : "pointer",
              }}
            >
              下一页 →
            </button>
          </div>
        </>
      )}
    </div>
  )
}

function SettingsPage() {
  const [providers, setProviders] = useState<ProviderView[]>([])
  const [preferences, setPreferences] = useState<Preferences>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [saveMsg, setSaveMsg] = useState("")
  const [saveMsgType, setSaveMsgType] = useState<"success" | "error">("success")
  const [connectionTesting, setConnectionTesting] = useState<string | null>(null)
  const [connectionResult, setConnectionResult] = useState<Record<string, string>>({})
  const [addProviderNotice, setAddProviderNotice] = useState("")

  // Provider form state (per provider)
  const [providerForms, setProviderForms] = useState<
    Record<string, { apiKey: string; showKey: boolean; endpoint: string; model: string }>
  >({})

  useEffect(() => {
    Promise.all([listProviders(), getPreferences()])
      .then(([providerList, prefs]) => {
        // fake-default 仅用于离线测试，正式 UI 不展示。
        const visible = providerList.filter((p) => p.profile_id !== "fake-default")
        setProviders(visible)
        setPreferences(prefs)
        // 依据 AI Provider 目录初始化可配置 Provider 的表单（排除 coming soon）。
        const forms: Record<string, { apiKey: string; showKey: boolean; endpoint: string; model: string }> = {}
        AI_PROVIDER_CATALOG.forEach((entry) => {
          if (entry.comingSoon) return
          const real = visible.find((p) => p.profile_id === entry.profileId)
          forms[entry.profileId] = {
            apiKey: "",
            showKey: false,
            endpoint: real?.endpoint || "",
            model: real?.model || "",
          }
        })
        setProviderForms(forms)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const showSaveMsg = (msg: string, type: "success" | "error" = "success") => {
    setSaveMsg(msg)
    setSaveMsgType(type)
    setTimeout(() => setSaveMsg(""), 3000)
  }

  const handleSavePreference = async (key: string, value: string) => {
    setSaving((prev) => ({ ...prev, [key]: true }))
    try {
      const updated = await updatePreferences({ [key]: value })
      setPreferences(updated)
      showSaveMsg("已保存")
    } catch (err) {
      showSaveMsg(err instanceof Error ? err.message : "保存失败", "error")
    } finally {
      setSaving((prev) => ({ ...prev, [key]: false }))
    }
  }

  const handleSaveProviderSettings = async (profileId: string) => {
    const form = providerForms[profileId]
    if (!form) return
    setSaving((prev) => ({ ...prev, [`provider-${profileId}`]: true }))
    try {
      // Save API Key if provided
      if (form.apiKey.trim()) {
        await updateProviderCredential(profileId, form.apiKey.trim())
      }
      // Save endpoint and model
      await updateProviderProfile(profileId, {
        endpoint: form.endpoint || null,
        model: form.model || null,
      })
      // Refresh providers
      const updatedList = await listProviders()
      setProviders(updatedList)
      showSaveMsg("Provider 设置已保存")
    } catch (err) {
      showSaveMsg(err instanceof Error ? err.message : "保存 Provider 失败", "error")
    } finally {
      setSaving((prev) => ({ ...prev, [`provider-${profileId}`]: false }))
    }
  }

  const handleTestConnection = async (profileId: string) => {
    setConnectionTesting(profileId)
    setConnectionResult((prev) => ({ ...prev, [profileId]: "" }))
    try {
      await testProviderConnection(profileId)
      setConnectionResult((prev) => ({ ...prev, [profileId]: "success" }))
    } catch (err) {
      setConnectionResult((prev) => ({
        ...prev,
        [profileId]: err instanceof Error ? err.message : "连接失败",
      }))
    } finally {
      setConnectionTesting(null)
    }
  }

  const handleAddProvider = () => {
    // 本版本仅提示，不实现真实新增。
    setAddProviderNotice("AI Provider management will be available in V2.4.")
  }

  const sectionStyle: CSSProperties = {
    marginBottom: 32,
    padding: 20,
    border: "1px solid #e0e0e0",
    borderRadius: 10,
    background: "#fff",
  }

  const sectionTitleStyle: CSSProperties = {
    margin: "0 0 16px 0",
    fontSize: "1.1rem",
    fontWeight: 600,
    color: "#333",
    paddingBottom: 8,
    borderBottom: "2px solid #e0e0e0",
  }

  const labelStyle: CSSProperties = {
    display: "block",
    marginBottom: 6,
    fontWeight: 500,
    color: "#555",
    fontSize: "0.9rem",
  }

  const inputStyle: CSSProperties = {
    width: "100%",
    fontSize: "0.95rem",
    padding: "8px 10px",
    boxSizing: "border-box",
    border: "1px solid #ccc",
    borderRadius: 6,
  }

  const selectStyle: CSSProperties = {
    ...inputStyle,
    width: "100%",
  }

  const checkboxRowStyle: CSSProperties = {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  }

  const btnPrimaryStyle: CSSProperties = {
    padding: "8px 20px",
    fontSize: "0.9rem",
    fontWeight: 500,
    color: "#fff",
    background: "#1565c0",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  }

  const btnSecondaryStyle: CSSProperties = {
    padding: "6px 16px",
    fontSize: "0.85rem",
    color: "#1565c0",
    background: "#e3f2fd",
    border: "1px solid #90caf9",
    borderRadius: 6,
    cursor: "pointer",
  }

  const formGroupStyle: CSSProperties = {
    marginBottom: 14,
  }

  const capabilityTagStyle: CSSProperties = {
    display: "inline-block",
    marginLeft: 4,
    marginRight: 4,
    padding: "2px 8px",
    fontSize: "0.75rem",
    borderRadius: 10,
    background: "#eef2f7",
    color: "#37474f",
    border: "1px solid #d6dde6",
  }

  // 依据前端目录渲染 Provider 卡片；real 为后端真实数据（用于配置状态）。
  const displayProviders = AI_PROVIDER_CATALOG.map((entry) => ({
    ...entry,
    real: providers.find((p) => p.profile_id === entry.profileId),
  }))

  return (
    <div style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0, color: "#333" }}>设置</h2>

      {saveMsg && (
        <div
          style={{
            padding: "10px 16px",
            marginBottom: 16,
            borderRadius: 6,
            background: saveMsgType === "success" ? "#e6f7e6" : "#fde8e8",
            color: saveMsgType === "success" ? "#2e7d32" : "#c62828",
            border: `1px solid ${saveMsgType === "success" ? "#a5d6a7" : "#ef9a9a"}`,
            fontSize: "0.9rem",
          }}
        >
          {saveMsgType === "success" ? "✅ " : "❌ "}
          {saveMsg}
        </div>
      )}

      {loading && <div style={{ color: "#888" }}>加载中...</div>}

      {!loading && (
        <>
          {/* ============ 一、AI Provider Library ============ */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>一、AI Provider Library</h3>

            {displayProviders.map((entry) => {
              const real = entry.real
              const form = providerForms[entry.profileId]
              const isTesting = connectionTesting === entry.profileId
              const connResult = connectionResult[entry.profileId]
              const configured = !!real?.credential.configured

              if (entry.comingSoon) {
                return (
                  <div
                    key={entry.profileId}
                    style={{
                      padding: 16,
                      marginBottom: 12,
                      border: "1px solid #e0e0e0",
                      borderRadius: 8,
                      background: "#f5f5f5",
                      opacity: 0.75,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 8,
                      }}
                    >
                      <span style={{ fontWeight: 600, color: "#333", fontSize: "1rem" }}>
                        {entry.displayName}
                      </span>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          padding: "2px 10px",
                          borderRadius: 12,
                          background: "#eeeeee",
                          color: "#888",
                          border: "1px solid #dddddd",
                        }}
                      >
                        Coming Soon
                      </span>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#888", marginBottom: 8 }}>
                      Type: AI Provider
                    </div>
                    <div style={{ marginBottom: 6 }}>
                      <span style={{ fontSize: "0.8rem", color: "#555", fontWeight: 500 }}>
                        Capabilities:
                      </span>
                      {entry.capabilities.map((cap) => (
                        <span key={cap} style={capabilityTagStyle}>
                          {cap}
                        </span>
                      ))}
                    </div>
                    <div>
                      <span style={{ fontSize: "0.8rem", color: "#555", fontWeight: 500 }}>
                        Sensitive File:
                      </span>{" "}
                      <span
                        style={{
                          fontSize: "0.8rem",
                          color: entry.sensitiveAllowed ? "#2e7d32" : "#888",
                        }}
                      >
                        {entry.sensitiveAllowed ? "Allowed" : "Not Allowed"}
                      </span>
                    </div>
                  </div>
                )
              }

              return (
                <div
                  key={entry.profileId}
                  style={{
                    padding: 16,
                    marginBottom: 12,
                    border: "1px solid #e0e0e0",
                    borderRadius: 8,
                    background: "#fafafa",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 10,
                    }}
                  >
                    <span style={{ fontWeight: 600, color: "#333", fontSize: "1rem" }}>
                      {entry.displayName}
                    </span>
                    <span
                      style={{
                        fontSize: "0.8rem",
                        padding: "2px 10px",
                        borderRadius: 12,
                        background: configured ? "#e6f7e6" : "#fde8e8",
                        color: configured ? "#2e7d32" : "#c62828",
                      }}
                    >
                      {configured
                        ? `已配置 ${real?.credential.masked ?? ""}`
                        : "未配置 API Key"}
                    </span>
                  </div>

                  <div style={{ fontSize: "0.8rem", color: "#888", marginBottom: 8 }}>
                    Type: AI Provider
                  </div>

                  <div style={{ marginBottom: 6 }}>
                    <span style={{ fontSize: "0.8rem", color: "#555", fontWeight: 500 }}>
                      Capabilities:
                    </span>
                    {entry.capabilities.map((cap) => (
                      <span key={cap} style={capabilityTagStyle}>
                        {cap}
                      </span>
                    ))}
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <span style={{ fontSize: "0.8rem", color: "#555", fontWeight: 500 }}>
                      Sensitive File:
                    </span>{" "}
                    <span
                      style={{
                        fontSize: "0.8rem",
                        color: entry.sensitiveAllowed ? "#2e7d32" : "#c62828",
                      }}
                    >
                      {entry.sensitiveAllowed ? "Allowed" : "Not Allowed"}
                    </span>
                  </div>

                  {/* API Key */}
                  <div style={formGroupStyle}>
                    <label style={labelStyle}>API Key</label>
                    <div style={{ display: "flex", gap: 8 }}>
                      <input
                        type={form?.showKey ? "text" : "password"}
                        value={form?.apiKey || ""}
                        onChange={(e) =>
                          setProviderForms((prev) => ({
                            ...prev,
                            [entry.profileId]: {
                              ...prev[entry.profileId],
                              apiKey: e.target.value,
                            },
                          }))
                        }
                        placeholder={configured ? "输入新 API Key 以替换现有密钥" : "输入 API Key"}
                        style={{ ...inputStyle, flex: 1 }}
                      />
                      <button
                        onClick={() =>
                          setProviderForms((prev) => ({
                            ...prev,
                            [entry.profileId]: {
                              ...prev[entry.profileId],
                              showKey: !prev[entry.profileId]?.showKey,
                            },
                          }))
                        }
                        style={{
                          padding: "8px 12px",
                          fontSize: "0.85rem",
                          color: "#555",
                          background: "#f5f5f5",
                          border: "1px solid #ccc",
                          borderRadius: 6,
                          cursor: "pointer",
                          whiteSpace: "nowrap",
                        }}
                        title={form?.showKey ? "隐藏" : "显示"}
                      >
                        {form?.showKey ? "隐藏" : "显示"}
                      </button>
                    </div>
                  </div>

                  {/* Base URL */}
                  <div style={formGroupStyle}>
                    <label style={labelStyle}>Base URL</label>
                    <input
                      type="text"
                      value={form?.endpoint || ""}
                      onChange={(e) =>
                        setProviderForms((prev) => ({
                          ...prev,
                          [entry.profileId]: {
                            ...prev[entry.profileId],
                            endpoint: e.target.value,
                          },
                        }))
                      }
                      placeholder={real?.endpoint || "输入 API 端点地址"}
                      style={inputStyle}
                    />
                  </div>

                  {/* Actions */}
                  <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                    <button
                      onClick={() => handleSaveProviderSettings(entry.profileId)}
                      disabled={!!saving[`provider-${entry.profileId}`]}
                      style={{
                        ...btnPrimaryStyle,
                        opacity: saving[`provider-${entry.profileId}`] ? 0.7 : 1,
                      }}
                    >
                      {saving[`provider-${entry.profileId}`] ? "保存中..." : "Save"}
                    </button>
                    <button
                      onClick={() => handleTestConnection(entry.profileId)}
                      disabled={isTesting || !configured}
                      style={{
                        ...btnSecondaryStyle,
                        opacity: isTesting || !configured ? 0.6 : 1,
                        cursor: isTesting || !configured ? "not-allowed" : "pointer",
                      }}
                    >
                      {isTesting ? "测试中..." : "Test Connection"}
                    </button>
                    {connResult && (
                      <span
                        style={{
                          fontSize: "0.85rem",
                          color: connResult === "success" ? "#2e7d32" : "#c62828",
                        }}
                      >
                        {connResult === "success" ? "✅ 连接成功" : `❌ ${connResult}`}
                      </span>
                    )}
                    <button
                      disabled
                      title="Default providers cannot be deleted in this version."
                      style={{
                        marginLeft: "auto",
                        padding: "6px 16px",
                        fontSize: "0.85rem",
                        color: "#9e9e9e",
                        background: "#f5f5f5",
                        border: "1px solid #e0e0e0",
                        borderRadius: 6,
                        cursor: "not-allowed",
                      }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )
            })}

            {/* Add AI Provider（本版本仅提示，不实现真实新增） */}
            <div style={{ marginTop: 4 }}>
              <button
                onClick={handleAddProvider}
                style={{
                  padding: "8px 20px",
                  fontSize: "0.9rem",
                  fontWeight: 500,
                  color: "#1565c0",
                  background: "#e3f2fd",
                  border: "1px solid #90caf9",
                  borderRadius: 6,
                  cursor: "pointer",
                }}
              >
                + Add AI Provider
              </button>
              {addProviderNotice && (
                <div
                  style={{
                    marginTop: 10,
                    padding: "10px 14px",
                    borderRadius: 6,
                    background: "#fff3cd",
                    border: "1px solid #ffe082",
                    fontSize: "0.9rem",
                    color: "#856404",
                  }}
                >
                  {addProviderNotice}
                </div>
              )}
            </div>
          </div>

          {/* ============ 二、Default Workflow Configuration ============ */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>二、Default Workflow Configuration</h3>

            <div style={formGroupStyle}>
              <label style={labelStyle}>Default OCR Provider</label>
              <div style={{ fontSize: "0.95rem", color: "#333" }}>{DEFAULT_OCR_PROVIDER}</div>
            </div>

            <div style={formGroupStyle}>
              <label style={labelStyle}>Default Translation Provider</label>
              <div style={{ fontSize: "0.95rem", color: "#333" }}>{DEFAULT_TRANSLATION_PROVIDER}</div>
            </div>

            <div style={{ fontSize: "0.8rem", color: "#666", lineHeight: 1.6 }}>
              New Task page will use these defaults.
              <br />
              若开启敏感文件，仅允许选择 Sensitive File Allowed 的 Provider。
            </div>
          </div>

          {/* ============ 三、OCR 参数 ============ */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>三、OCR 参数</h3>

            <div style={formGroupStyle}>
              <label style={labelStyle} htmlFor="ocr-language">
                文档语言
              </label>
              <select
                id="ocr-language"
                value={preferences["ocr_language"] || "auto"}
                onChange={(e) => handleSavePreference("ocr_language", e.target.value)}
                style={selectStyle}
              >
                <option value="auto">自动</option>
                <option value="zh">中文</option>
                <option value="en">英文</option>
                <option value="ja">日文</option>
                <option value="other">其它（如 Provider 支持）</option>
              </select>
              <div style={{ marginTop: 4, fontSize: "0.8rem", color: "#888" }}>
                {saving["ocr_language"] ? "保存中..." : ""}
              </div>
            </div>

            <div style={checkboxRowStyle}>
              <input
                type="checkbox"
                id="sensitive-mode"
                checked={preferences["sensitive_file_mode"] === "true"}
                onChange={(e) =>
                  handleSavePreference(
                    "sensitive_file_mode",
                    e.target.checked ? "true" : "false",
                  )
                }
              />
              <label htmlFor="sensitive-mode" style={{ fontSize: "0.9rem", color: "#555", cursor: "pointer" }}>
                敏感文件模式
              </label>
            </div>
          </div>

          {/* ============ 四、PDF 默认设置 ============ */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>四、PDF 默认设置</h3>

            <div style={checkboxRowStyle}>
              <input
                type="checkbox"
                id="process-all-pages"
                checked={preferences["pdf_process_all_pages"] !== "false"}
                onChange={(e) =>
                  handleSavePreference(
                    "pdf_process_all_pages",
                    e.target.checked ? "true" : "false",
                  )
                }
              />
              <label htmlFor="process-all-pages" style={{ fontSize: "0.9rem", color: "#555", cursor: "pointer" }}>
                默认处理全部页面
              </label>
            </div>

            <div style={formGroupStyle}>
              <label style={labelStyle} htmlFor="default-page-range">
                默认页码范围（可为空）
              </label>
              <input
                id="default-page-range"
                type="text"
                value={preferences["pdf_default_page_range"] || ""}
                onChange={(e) =>
                  handleSavePreference("pdf_default_page_range", e.target.value)
                }
                placeholder="例如：1-3,5,7-9"
                style={inputStyle}
              />
              <div style={{ marginTop: 4, fontSize: "0.8rem", color: "#888" }}>
                {saving["pdf_default_page_range"] ? "保存中..." : "上传时自动带入，但允许用户修改"}
              </div>
            </div>
          </div>

          {/* ============ 五、输出设置 ============ */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>五、输出设置</h3>

            <div style={formGroupStyle}>
              <label style={labelStyle} htmlFor="default-output-dir">
                默认输出目录
              </label>
              <input
                id="default-output-dir"
                type="text"
                value={preferences["output_default_dir"] || ""}
                onChange={(e) =>
                  handleSavePreference("output_default_dir", e.target.value)
                }
                placeholder="默认输出目录路径"
                style={inputStyle}
              />
            </div>

            <div style={checkboxRowStyle}>
              <input
                type="checkbox"
                id="same-as-input"
                checked={preferences["output_same_as_input"] === "true"}
                onChange={(e) =>
                  handleSavePreference(
                    "output_same_as_input",
                    e.target.checked ? "true" : "false",
                  )
                }
              />
              <label htmlFor="same-as-input" style={{ fontSize: "0.9rem", color: "#555", cursor: "pointer" }}>
                默认与输入文件同目录
              </label>
            </div>
            {preferences["output_same_as_input"] === "true" && (
              <div style={{ marginTop: 4, fontSize: "0.8rem", color: "#888" }}>
                开启后，自动使用：输入目录/GreatOCR_Output/
              </div>
            )}
          </div>

          {/* ============ 六、结果设置 ============ */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>六、结果设置</h3>

            <div style={checkboxRowStyle}>
              <input
                type="checkbox"
                id="export-docx"
                checked={preferences["result_export_docx"] !== "false"}
                onChange={(e) =>
                  handleSavePreference(
                    "result_export_docx",
                    e.target.checked ? "true" : "false",
                  )
                }
              />
              <label htmlFor="export-docx" style={{ fontSize: "0.9rem", color: "#555", cursor: "pointer" }}>
                默认导出 DOCX
              </label>
            </div>

            <div style={checkboxRowStyle}>
              <input
                type="checkbox"
                id="generate-quality-report"
                checked={preferences["result_generate_quality_report"] !== "false"}
                onChange={(e) =>
                  handleSavePreference(
                    "result_generate_quality_report",
                    e.target.checked ? "true" : "false",
                  )
                }
              />
              <label htmlFor="generate-quality-report" style={{ fontSize: "0.9rem", color: "#555", cursor: "pointer" }}>
                生成 Quality Report
              </label>
            </div>
          </div>

          {/* ============ 七、配置管理 ============ */}
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>七、配置管理</h3>
            <div style={{ fontSize: "0.9rem", color: "#555", lineHeight: 1.8 }}>
              <p style={{ margin: 0 }}>
                ✅ 所有配置已持久化保存到本地 SQLite 数据库。
              </p>
              <p style={{ margin: "4px 0" }}>
                ✅ 重启程序后仍然有效。
              </p>
              <p style={{ margin: "4px 0" }}>
                ✅ 配置仅保存在本机，不会写入 Git 仓库。
              </p>
              <p style={{ margin: "4px 0" }}>
                ✅ API Key 存储在操作系统凭据管理器（keyring）中，不进入 Git。
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function HomePage() {
  return (
    <div style={{ padding: "3rem 2rem", textAlign: "center", color: "#666", fontSize: "1.1rem" }}>
      <h2 style={{ color: "#333" }}>欢迎使用 GreatOCR</h2>
      <p style={{ marginTop: "1rem", color: "#888" }}>
        本地文档处理工具：PDF 重建、OCR 处理与结果查看
      </p>
      <div style={{ marginTop: "2rem" }}>
        <Link
          to="/new"
          style={{
            display: "inline-block",
            padding: "12px 32px",
            fontSize: "1rem",
            fontWeight: 600,
            color: "#fff",
            background: "#1565c0",
            borderRadius: 6,
            textDecoration: "none",
          }}
        >
          开始新 OCR 任务
        </Link>
      </div>
    </div>
  )
}

const navLinkStyle: CSSProperties = {
  textDecoration: "none",
  color: "#1565c0",
  fontWeight: 500,
  padding: "0.4rem 0.8rem",
  borderRadius: 6,
}

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "0.75rem 1.5rem",
  borderBottom: "1px solid #e0e0e0",
  background: "#fafafa",
}

const navStyle: CSSProperties = {
  display: "flex",
  gap: "0.25rem",
}

export function App() {
  return (
    <div
      style={{
        minHeight: "100vh",
        fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
      }}
    >
      <header style={headerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <h1 style={{ margin: 0, fontSize: "1.25rem", color: "#333" }}>GreatOCR</h1>
          <nav style={navStyle}>
            <Link to="/" style={navLinkStyle}>
              首页
            </Link>
            <Link to="/tasks" style={navLinkStyle}>
              任务中心
            </Link>
            <Link to="/new" style={navLinkStyle}>
              新建任务
            </Link>
            <Link to="/settings" style={navLinkStyle}>
              设置
            </Link>
          </nav>
        </div>
        <HealthBadge />
      </header>

      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/tasks" element={<TaskCenterPage />} />
          <Route path="/new" element={<NewTaskPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  )
}
