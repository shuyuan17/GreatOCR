import { useEffect, useState } from "react"
import { Link, Route, Routes } from "react-router-dom"
import { apiFetch } from "./api"

/* ------------------------------------------------------------------ */
/*  Health check badge                                                 */
/* ------------------------------------------------------------------ */

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

/* ------------------------------------------------------------------ */
/*  Placeholder pages for V2.3 Task 6                                 */
/* ------------------------------------------------------------------ */

const placeholderStyle: React.CSSProperties = {
  padding: "3rem 2rem",
  textAlign: "center",
  color: "#666",
  fontSize: "1.1rem",
}

function TaskCenterPage() {
  return <div style={placeholderStyle}>📋 任务中心 — 即将在 V2.3 Task 6 中实现</div>
}

function NewTaskPage() {
  return <div style={placeholderStyle}>➕ 新建任务 — 即将在 V2.3 Task 6 中实现</div>
}

function SettingsPage() {
  return <div style={placeholderStyle}>⚙️ 设置 — 即将在 V2.3 Task 6 中实现</div>
}

function HomePage() {
  return (
    <div style={placeholderStyle}>
      <h2>欢迎使用 GreatOCR</h2>
      <p style={{ marginTop: "1rem", color: "#888" }}>
        本地文档处理工具 — PDF 重建 · 图片增强 · 多语言翻译
      </p>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  App shell                                                          */
/* ------------------------------------------------------------------ */

const navLinkStyle: React.CSSProperties = {
  textDecoration: "none",
  color: "#1565c0",
  fontWeight: 500,
  padding: "0.4rem 0.8rem",
  borderRadius: 6,
}

const activeNavLinkStyle: React.CSSProperties = {
  ...navLinkStyle,
  background: "#e3f2fd",
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
