import { useCallback, useEffect, useRef, useState } from "react"
import { Link, Route, Routes, useNavigate } from "react-router-dom"
import { apiFetch, getTask, listProviders, startTask, uploadFile, type ProviderView, type TaskRecord, type TaskStatus } from "./api"
import { isPdfFile, validatePageRange } from "./pageRanges"

/* ================================================================== */
/*  Health check badge                                                 */
/* ================================================================== */

type HealthState = "loading" | "ok" | "error"

function HealthBadge() {
  const [state, setState] = useState<HealthState>("loading")
  const [label, setLabel] = useState("正在连接后端…")

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

  const indicator =
    state === "loading" ? "🔄" : state === "ok" ? "✅" : "❌"

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

/* ================================================================== */
/*  状态中文名称                                                        */
/* ================================================================== */

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

/* ================================================================== */
/*  文件尺寸格式化                                                      */
/* ================================================================== */

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/* ================================================================== */
/*  新建任务 — 上传 + OCR                                              */
/* ================================================================== */

function NewTaskPage() {
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [providers, setProviders] = useState<ProviderView[]>([])
  const [selectedProvider, setSelectedProvider] = useState("fake-default")
  const [pageRange, setPageRange] = useState("")
  const [phase, setPhase] = useState<"idle" | "uploading" | "starting" | "running" | "done" | "error">("idle")
  const [task, setTask] = useState<TaskRecord | null>(null)
  const [errorMsg, setErrorMsg] = useState("")
  const [progressMsg, setProgressMsg] = useState("")
  const pageRangeError = validatePageRange(pageRange)
  const pdfSelected = isPdfFile(file)

  // 加载 Provider 列表
  useEffect(() => {
    listProviders()
      .then((list) => {
        setProviders(list)
        if (list.length > 0 && list[0].profile_id) {
          setSelectedProvider(list[0].profile_id)
        }
      })
      .catch(() => {})
  }, [])

  // 轮询任务状态
  const pollTask = useCallback(async (taskId: string) => {
    const maxAttempts = 120 // 最多等 2 分钟
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const t = await getTask(taskId)
        setTask(t)
        setProgressMsg(STATUS_LABELS[t.status])

        if (["succeeded", "failed", "partial", "cancelled"].includes(t.status)) {
          setPhase("done")
          return
        }
        if (t.status === "running") {
          setPhase("running")
        }
      } catch {
        // 继续轮询
      }
      await new Promise((r) => setTimeout(r, 1000))
    }
    setPhase("error")
    setErrorMsg("轮询超时，请刷新页面查看任务状态")
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
    setProgressMsg("正在上传文件…")

    try {
      // 1. 上传文件 → 创建任务
      const result = await uploadFile(file, {
        providerProfileId: selectedProvider,
        pages: pdfSelected ? pageRange : "",
      })
      setTask(result.task)
      setProgressMsg("文件已上传，正在启动 OCR…")

      // 2. 启动任务
      setPhase("starting")
      const started = await startTask(result.task.task_id)
      setTask(started)

      // 3. 轮询等待完成
      setPhase("running")
      setProgressMsg("任务已加入队列，等待处理…")
      await pollTask(result.task.task_id)
    } catch (err: unknown) {
      setPhase("error")
      setErrorMsg(err instanceof Error ? err.message : "操作失败")
    }
  }

  const providerReady = selectedProvider === "fake-default" ||
    providers.find((p) => p.profile_id === selectedProvider)?.credential?.configured

  const statusStyle: React.CSSProperties = {
    marginTop: 16,
    padding: "12px 16px",
    borderRadius: 8,
    fontSize: "0.95rem",
    lineHeight: 1.6,
  }

  return (
    <div style={{ padding: "2rem", maxWidth: 640, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0, color: "#333" }}>新建 OCR 任务</h2>

      {/* 文件选择 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}>
          选择文件（图片或 PDF）
        </label>
        <input
          id="source-file"
          aria-label="选择文件（图片或 PDF）"
          ref={fileRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.tif,.bmp"
          onChange={(e) => {
            const nextFile = e.target.files?.[0] ?? null
            setFile(nextFile)
            setErrorMsg("")
            if (!isPdfFile(nextFile)) {
              setPageRange("")
            }
          }}
          disabled={phase !== "idle"}
          style={{ fontSize: "0.95rem" }}
        />
        {file && (
          <div style={{ marginTop: 6, fontSize: "0.85rem", color: "#666" }}>
            {file.name} ({formatSize(file.size)})
          </div>
        )}
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}>
          页码范围
        </label>
        <input
          id="page-range"
          aria-label="页码范围"
          type="text"
          value={pageRange}
          onChange={(e) => {
            setPageRange(e.target.value)
            setErrorMsg("")
          }}
          disabled={phase !== "idle" || !pdfSelected}
          placeholder="留空处理全部页面；示例：1-3,5,7-9"
          style={{ width: "100%", fontSize: "0.95rem", padding: "8px 10px", boxSizing: "border-box" }}
        />
        <div style={{ marginTop: 6, fontSize: "0.8rem", color: pageRangeError ? "#c62828" : "#666" }}>
          {pageRangeError || (pdfSelected ? "支持 1、1-3、1,3,5、1-3,5,7-9；留空表示全部页面" : "仅 PDF 支持页码范围")}
        </div>
      </div>

      {/* Provider 选择 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: "block", marginBottom: 6, fontWeight: 500, color: "#555" }}>
          OCR Provider
        </label>
        <select
          id="provider-select"
          aria-label="OCR Provider"
          value={selectedProvider}
          onChange={(e) => setSelectedProvider(e.target.value)}
          disabled={phase !== "idle"}
          style={{ fontSize: "0.95rem", padding: "4px 8px" }}
        >
          {providers.map((p) => (
            <option key={p.profile_id} value={p.profile_id}>
              {p.display_name} {p.credential?.configured ? "✅" : "⚠️ 未配置"}
            </option>
          ))}
        </select>
        {selectedProvider !== "fake-default" && !providerReady && (
          <div style={{ marginTop: 4, fontSize: "0.8rem", color: "#c62828" }}>
            ⚠️ 该 Provider 未配置 API Key，请在"设置"中先配置
          </div>
        )}
      </div>

      {/* 开始按钮 */}
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
        {phase === "idle" ? "开始 OCR" :
         phase === "uploading" ? "上传中…" :
         phase === "starting" ? "启动中…" :
         phase === "running" ? "OCR 处理中…" :
         "完成"}
      </button>

      {/* 进度 / 状态 */}
      {phase !== "idle" && (
        <div style={{
          ...statusStyle,
          background: phase === "error" ? "#fde8e8" : phase === "done" && task?.status === "succeeded" ? "#e6f7e6" : "#e3f2fd",
          color: phase === "error" ? "#c62828" : phase === "done" && task?.status === "succeeded" ? "#2e7d32" : "#1565c0",
        }}>
          <div><strong>状态：</strong>{progressMsg}</div>
          {task && (
            <>
              <div><strong>任务 ID：</strong><code style={{ fontSize: "0.85rem" }}>{task.task_id}</code></div>
              <div><strong>文件名：</strong>{task.display_name}</div>
              {task.status !== "running" && task.status !== "pending" && (
                <div><strong>输出目录：</strong><code style={{ fontSize: "0.85rem" }}>{task.output_dir}</code></div>
              )}
              {task.quality_rating && (
                <div><strong>质量评分：</strong>{task.quality_rating}</div>
              )}
            </>
          )}
          {errorMsg && <div style={{ marginTop: 8, color: "#c62828" }}>❌ {errorMsg}</div>}
        </div>
      )}

      {phase === "done" && task && (
        <div style={{ marginTop: 16 }}>
          <button
            onClick={() => navigate("/tasks")}
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
            查看任务列表
          </button>
        </div>
      )}
    </div>
  )
}

/* ================================================================== */
/*  任务中心 — 简单列表                                                */
/* ================================================================== */

function TaskCenterPage() {
  const [tasks, setTasks] = useState<TaskRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const list = await (await import("./api")).listTasks()
        if (!cancelled) setTasks(list)
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    const timer = setInterval(load, 5000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  return (
    <div style={{ padding: "2rem", maxWidth: 800, margin: "0 auto" }}>
      <h2 style={{ marginTop: 0, color: "#333" }}>任务中心</h2>

      {loading && <div style={{ color: "#888" }}>加载中…</div>}

      {!loading && tasks.length === 0 && (
        <div style={{ color: "#888", padding: "2rem 0", textAlign: "center" }}>
          暂无任务，请前往「新建任务」开始。
        </div>
      )}

      {tasks.map((t) => (
        <div
          key={t.task_id}
          style={{
            padding: "12px 16px",
            marginBottom: 8,
            border: "1px solid #e0e0e0",
            borderRadius: 8,
            background: "#fafafa",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: 500 }}>{t.display_name}</span>
            <span
              style={{
                fontSize: "0.8rem",
                padding: "2px 10px",
                borderRadius: 12,
                background: `${STATUS_COLORS[t.status]}18`,
                color: STATUS_COLORS[t.status],
                border: `1px solid ${STATUS_COLORS[t.status]}40`,
              }}
            >
              {STATUS_LABELS[t.status]}
            </span>
          </div>
          <div style={{ marginTop: 6, fontSize: "0.85rem", color: "#888" }}>
            ID: <code>{t.task_id.slice(0, 12)}…</code> · Provider: {t.provider_profile_id}
          </div>
          {t.quality_rating && (
            <div style={{ marginTop: 4, fontSize: "0.85rem", color: "#2e7d32" }}>
              质量评分: {t.quality_rating}
            </div>
          )}
          {t.status === "succeeded" && (
            <div style={{ marginTop: 4, fontSize: "0.85rem", color: "#666" }}>
              输出: <code>{t.output_dir}</code>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

/* ================================================================== */
/*  设置 — Provider 配置                                              */
/* ================================================================== */

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

      {loading && <div style={{ color: "#888" }}>加载中…</div>}

      {providers.map((p) => (
        <div
          key={p.profile_id}
          style={{
            padding: "12px 16px",
            marginBottom: 8,
            border: "1px solid #e0e0e0",
            borderRadius: 8,
            background: "#fafafa",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: 500 }}>{p.display_name}</span>
            <span
              style={{
                fontSize: "0.8rem",
                padding: "2px 10px",
                borderRadius: 12,
                background: p.credential.configured ? "#e6f7e6" : "#fde8e8",
                color: p.credential.configured ? "#2e7d32" : "#c62828",
              }}
            >
              {p.credential.configured ? `✅ 已配置 ${p.credential.masked}` : "❌ 未配置 API Key"}
            </span>
          </div>
          <div style={{ marginTop: 6, fontSize: "0.85rem", color: "#888" }}>
            ID: {p.profile_id} · 类型: {p.adapter_type}
          </div>
        </div>
      ))}

      <div style={{ marginTop: 24, padding: 16, border: "1px solid #e0e0e0", borderRadius: 8, background: "#fff3cd" }}>
        <strong style={{ color: "#856404" }}>如何配置 MinerU API Key</strong>
        <pre style={{
          marginTop: 8,
          padding: 12,
          background: "#fff",
          border: "1px solid #ffe082",
          borderRadius: 6,
          fontSize: "0.8rem",
          overflow: "auto",
          whiteSpace: "pre-wrap",
        }}>
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

/* ================================================================== */
/*  首页                                                                */
/* ================================================================== */

function HomePage() {
  return (
    <div style={{ padding: "3rem 2rem", textAlign: "center", color: "#666", fontSize: "1.1rem" }}>
      <h2 style={{ color: "#333" }}>欢迎使用 GreatOCR</h2>
      <p style={{ marginTop: "1rem", color: "#888" }}>
        本地文档处理工具 — PDF 重建 · 图片增强 · 多语言翻译
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
            border: "none",
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

/* ================================================================== */
/*  App shell                                                          */
/* ================================================================== */

const navLinkStyle: React.CSSProperties = {
  textDecoration: "none",
  color: "#1565c0",
  fontWeight: 500,
  padding: "0.4rem 0.8rem",
  borderRadius: 6,
}

const headerStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "0.75rem 1.5rem",
  borderBottom: "1px solid #e0e0e0",
  background: "#fafafa",
}

const navStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.25rem",
}

export function App() {
  return (
    <div style={{ minHeight: "100vh", fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif" }}>
      <header style={headerStyle}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <h1 style={{ margin: 0, fontSize: "1.25rem", color: "#333" }}>GreatOCR</h1>
          <nav style={navStyle}>
            <Link to="/" style={navLinkStyle}>首页</Link>
            <Link to="/tasks" style={navLinkStyle}>任务中心</Link>
            <Link to="/new" style={navLinkStyle}>新建任务</Link>
            <Link to="/settings" style={navLinkStyle}>设置</Link>
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
