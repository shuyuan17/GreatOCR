import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react"
import { Link, Route, Routes, useNavigate, useSearchParams } from "react-router-dom"
import {
  apiFetch,
  deleteTask,
  getDefaultOutputDir,
  getTask,
  getTaskResultFiles,
  listProviders,
  listTasks,
  openOutput,
  startTask,
  uploadFile,
  type ProviderView,
  type TaskRecord,
  type TaskResultSummary,
  type TaskStatus,
} from "./api"
import { isPdfFile, validatePageRange } from "./pageRanges"

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
    }
  }, [])

  const indicator = state === "loading" ? "⏳" : state === "ok" ? "✅" : "❌"

  return (
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
  )
}

function NewTaskPage() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [providers, setProviders] = useState<ProviderView[]>([])
  const [selectedProvider, setSelectedProvider] = useState("fake-default")
  const [pageRange, setPageRange] = useState("")
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

  const providerReady =
    selectedProvider === "fake-default" ||
    providers.find((provider) => provider.profile_id === selectedProvider)?.credential
      ?.configured

  const statusStyle: CSSProperties = {
    marginTop: 16,
    padding: "12px 16px",
    borderRadius: 8,
    fontSize: "0.95rem",
    lineHeight: 1.6,
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 640, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0, color: "#333" }}>新建 OCR 任务</h2>

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
          htmlFor="provider-select"
          style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}
        >
          OCR Provider
        </label>
        <select
          id="provider-select"
          aria-label="OCR Provider"
          value={selectedProvider}
          disabled={phase !== "idle"}
          onChange={(event) => setSelectedProvider(event.target.value)}
          style={{ fontSize: "0.95rem", padding: "4px 8px" }}
        >
          {providers.map((provider) => (
            <option key={provider.profile_id} value={provider.profile_id}>
              {provider.display_name}{" "}
              {provider.credential?.configured ? "已配置" : "未配置"}
            </option>
          ))}
        </select>
        {selectedProvider !== "fake-default" && !providerReady && (
          <div style={{ marginTop: 4, fontSize: "0.8rem", color: "#c62828" }}>
            当前 Provider 未配置 API Key，请先在设置中完成配置。
          </div>
        )}
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
        disabled={!file || phase !== "idle" || (!providerReady && selectedProvider !== "fake-default")}
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
          ? "开始 OCR"
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
  const [expandedTaskIds, setExpandedTaskIds] = useState<Record<string, boolean>>({})
  const [resultSummaries, setResultSummaries] = useState<Record<string, TaskResultSummary>>({})
  const [resultLoading, setResultLoading] = useState<Record<string, boolean>>({})
  const [resultErrors, setResultErrors] = useState<Record<string, string>>({})
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null)

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

  useEffect(() => {
    if (!focusTaskId) return
    const focusedTask = tasks.find((task) => task.task_id === focusTaskId)
    if (!focusedTask || !canViewResults(focusedTask.status)) return
    setExpandedTaskIds((current) =>
      current[focusTaskId] !== undefined ? current : { ...current, [focusTaskId]: true },
    )
  }, [focusTaskId, tasks])

  useEffect(() => {
    const taskIdsToLoad = tasks
      .filter((task) => expandedTaskIds[task.task_id] && canViewResults(task.status))
      .map((task) => task.task_id)
      .filter((taskId) => !resultSummaries[taskId] && !resultLoading[taskId] && !resultErrors[taskId])

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
            [taskId]: "结果信息暂时无法读取，请稍后再试。",
          }))
        })
        .finally(() => {
          setResultLoading((current) => ({ ...current, [taskId]: false }))
        })
    })
  }, [expandedTaskIds, resultErrors, resultLoading, resultSummaries, tasks])

  const toggleTask = (taskId: string) => {
    setExpandedTaskIds((current) => ({ ...current, [taskId]: !current[taskId] }))
  }

  const handleDelete = async (taskId: string) => {
    try {
      await deleteTask(taskId)
      setTasks((current) => current.filter((t) => t.task_id !== taskId))
      setExpandedTaskIds((current) => {
        const next = { ...current }
        delete next[taskId]
        return next
      })
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
      // 静默处理：文件管理器已打开或出错
    }
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 860, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0, color: "#333" }}>任务中心</h2>

      {loading && <div style={{ color: "#888" }}>加载中...</div>}

      {!loading && tasks.length === 0 && (
        <div style={{ color: "#888", padding: "2rem 0", textAlign: "center" }}>
          暂无任务，请前往“新建任务”开始。
        </div>
      )}

      {tasks.map((task) => {
        const expanded = !!expandedTaskIds[task.task_id]
        const summary = resultSummaries[task.task_id]
        const isLoadingResults = !!resultLoading[task.task_id]
        const resultError = resultErrors[task.task_id]
        const showToggle = canViewResults(task.status)

        return (
          <div
            key={task.task_id}
            style={{
              padding: "12px 16px",
              marginBottom: 12,
              border: "1px solid #e0e0e0",
              borderRadius: 10,
              background: focusTaskId === task.task_id ? "#f6fbff" : "#fafafa",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 12,
              }}
            >
              <span style={{ fontWeight: 600 }}>{task.display_name}</span>
              <span
                style={{
                  fontSize: "0.8rem",
                  padding: "2px 10px",
                  borderRadius: 12,
                  background: `${STATUS_COLORS[task.status]}18`,
                  color: STATUS_COLORS[task.status],
                  border: `1px solid ${STATUS_COLORS[task.status]}40`,
                }}
              >
                {STATUS_LABELS[task.status]}
              </span>
            </div>

            <div style={{ marginTop: 6, fontSize: "0.85rem", color: "#666" }}>
              ID: <code>{task.task_id.slice(0, 12)}...</code> · Provider: {task.provider_profile_id}
            </div>

            {task.quality_rating && (
              <div style={{ marginTop: 4, fontSize: "0.85rem", color: "#2e7d32" }}>
                质量评分: {task.quality_rating}
              </div>
            )}

            {showToggle && (
              <div style={{ marginTop: 10 }}>
                <button
                  onClick={() => toggleTask(task.task_id)}
                  style={{
                    padding: "6px 14px",
                    fontSize: "0.9rem",
                    color: "#1565c0",
                    background: "#e3f2fd",
                    border: "1px solid #90caf9",
                    borderRadius: 6,
                    cursor: "pointer",
                  }}
                >
                  {expanded ? "收起结果" : "查看结果"}
                </button>
              </div>
            )}

            {expanded && (
              <div
                style={{
                  marginTop: 12,
                  padding: 14,
                  borderRadius: 8,
                  background: "#fff",
                  border: "1px solid #dbe7f3",
                }}
              >
                <div style={{ fontSize: "0.9rem", color: "#333", lineHeight: 1.7 }}>
                  <div>
                    <strong>任务状态：</strong>
                    {STATUS_LABELS[task.status]}
                  </div>
                  <div>
                    <strong>文件名：</strong>
                    {task.display_name}
                  </div>
                  <div>
                    <strong>页码范围：</strong>
                    {formatPages(task.selected_pages)}
                  </div>
                  <div>
                    <strong>创建时间：</strong>
                    {formatDateTime(task.created_at)}
                  </div>
                  {task.completed_at && (
                    <div>
                      <strong>完成时间：</strong>
                      {formatDateTime(task.completed_at)}
                    </div>
                  )}
                  <div>
                    <strong>输出目录：</strong>
                    <code>{task.output_dir}</code>
                  </div>
                </div>

                <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    onClick={() => handleCopyPath(task.output_dir)}
                    style={{
                      padding: "6px 14px",
                      fontSize: "0.85rem",
                      color: copyFeedback === task.output_dir ? "#2e7d32" : "#1565c0",
                      background: copyFeedback === task.output_dir ? "#e6f7e6" : "#e3f2fd",
                      border: `1px solid ${copyFeedback === task.output_dir ? "#a5d6a7" : "#90caf9"}`,
                      borderRadius: 6,
                      cursor: "pointer",
                    }}
                  >
                    {copyFeedback === task.output_dir ? "✅ 已复制" : "复制输出路径"}
                  </button>
                  <button
                    onClick={() => handleOpenOutput(task.task_id)}
                    style={{
                      padding: "6px 14px",
                      fontSize: "0.85rem",
                      color: "#1565c0",
                      background: "#e3f2fd",
                      border: "1px solid #90caf9",
                      borderRadius: 6,
                      cursor: "pointer",
                    }}
                  >
                    打开输出文件夹
                  </button>
                  <button
                    onClick={() => setDeleteConfirmId(task.task_id)}
                    style={{
                      padding: "6px 14px",
                      fontSize: "0.85rem",
                      color: "#c62828",
                      background: "#fde8e8",
                      border: "1px solid #ef9a9a",
                      borderRadius: 6,
                      cursor: "pointer",
                    }}
                  >
                    删除任务
                  </button>
                </div>

                {deleteConfirmId === task.task_id && (
                  <div
                    style={{
                      marginTop: 10,
                      padding: "10px 14px",
                      borderRadius: 8,
                      background: "#fff3cd",
                      border: "1px solid #ffe082",
                      fontSize: "0.9rem",
                      color: "#856404",
                    }}
                  >
                    <div style={{ marginBottom: 8 }}>
                      ⚠️ 确认删除此任务记录？仅删除记录，不会删除输出文件。
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        onClick={() => handleDelete(task.task_id)}
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
                        onClick={() => setDeleteConfirmId(null)}
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

                {isLoadingResults && (
                  <div style={{ marginTop: 12, color: "#666", fontSize: "0.9rem" }}>
                    正在读取结果文件信息...
                  </div>
                )}

                {resultError && (
                  <div style={{ marginTop: 12, color: "#c62828", fontSize: "0.9rem" }}>
                    {resultError}
                  </div>
                )}

                {summary && (
                  <div style={{ marginTop: 14 }}>
                    <div style={{ fontWeight: 600, marginBottom: 10, color: "#333" }}>
                      可下载结果
                    </div>

                    <div style={{ display: "grid", gap: 10 }}>
                      <div
                        style={{
                          padding: 12,
                          borderRadius: 8,
                          background: "#f8fbff",
                          border: "1px solid #d7e7f7",
                        }}
                      >
                        <div style={{ marginBottom: 6, color: "#333" }}>
                          <strong>result.docx</strong>
                        </div>
                        {summary.files.result_docx.exists ? (
                          <a
                            href={summary.files.result_docx.download_path ?? "#"}
                            style={{ color: "#1565c0", textDecoration: "none", fontWeight: 500 }}
                          >
                            下载 result.docx
                          </a>
                        ) : (
                          <div style={{ color: "#666" }}>本次任务暂未生成可下载结果文件</div>
                        )}
                      </div>

                      <div
                        style={{
                          padding: 12,
                          borderRadius: 8,
                          background: "#f8fbff",
                          border: "1px solid #d7e7f7",
                        }}
                      >
                        <div style={{ marginBottom: 6, color: "#333" }}>
                          <strong>quality-report.docx</strong>
                        </div>
                        {summary.files.quality_report_docx.exists ? (
                          <a
                            href={summary.files.quality_report_docx.download_path ?? "#"}
                            style={{ color: "#1565c0", textDecoration: "none", fontWeight: 500 }}
                          >
                            下载 quality-report.docx
                          </a>
                        ) : (
                          <div style={{ color: "#666" }}>本次未生成质量报告</div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function SettingsPage() {
  const [providers, setProviders] = useState<ProviderView[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    listProviders()
      .then(setProviders)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0, color: "#333" }}>设置</h2>

      <h3 style={{ color: "#555" }}>OCR Provider</h3>

      {loading && <div style={{ color: "#888" }}>加载中...</div>}

      {providers.map((provider) => (
        <div
          key={provider.profile_id}
          style={{
            padding: "12px 16px",
            marginBottom: 8,
            border: "1px solid #e0e0e0",
            borderRadius: 8,
            background: "#fafafa",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: 500 }}>{provider.display_name}</span>
            <span
              style={{
                fontSize: "0.8rem",
                padding: "2px 10px",
                borderRadius: 12,
                background: provider.credential.configured ? "#e6f7e6" : "#fde8e8",
                color: provider.credential.configured ? "#2e7d32" : "#c62828",
              }}
            >
              {provider.credential.configured
                ? `已配置 ${provider.credential.masked}`
                : "未配置 API Key"}
            </span>
          </div>
          <div style={{ marginTop: 6, fontSize: "0.85rem", color: "#888" }}>
            ID: {provider.profile_id} · 类型: {provider.adapter_type}
          </div>
        </div>
      ))}

      <div
        style={{
          marginTop: 24,
          padding: 16,
          border: "1px solid #e0e0e0",
          borderRadius: 8,
          background: "#fff3cd",
        }}
      >
        <strong style={{ color: "#856404" }}>如何配置 MinerU API Key</strong>
        <pre
          style={{
            marginTop: 8,
            padding: 12,
            background: "#fff",
            border: "1px solid #ffe082",
            borderRadius: 6,
            fontSize: "0.8rem",
            overflow: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
{`# 启动后端后执行（替换 YOUR_API_KEY）
curl -X POST http://127.0.0.1:8399/api/providers \\
  -H "X-GreatOCR-Token: greatocr-dev-token-2026" \\
  -H "X-GreatOCR-Provider-Key: YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"profile_id":"mineru-default","display_name":"MinerU","adapter_type":"mineru","endpoint":"https://mineru.net","public":true,"capabilities":{"tables":true,"images":true}}'`}
        </pre>
      </div>
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
