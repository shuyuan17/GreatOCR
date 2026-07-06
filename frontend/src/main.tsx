import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import { App } from "./App"
import { resolveSessionToken } from "./sessionToken"

const root = createRoot(document.getElementById("root")!)

try {
  window.__GREAT_OCR_TOKEN__ = resolveSessionToken(import.meta.env.VITE_GREAT_OCR_TOKEN)

  root.render(
    <StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </StrictMode>,
  )
} catch (error) {
  const message =
    error instanceof Error
      ? error.message
      : "GreatOCR startup failed. Please restart via start.bat."

  root.render(
    <StrictMode>
      <div
        style={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
          background: "#fffaf5",
          color: "#8a2d1c",
          padding: "2rem",
        }}
      >
        <div
          style={{
            maxWidth: 640,
            background: "#fff",
            border: "1px solid #f3c7bf",
            borderRadius: 12,
            padding: "1.5rem",
            boxShadow: "0 8px 24px rgba(0, 0, 0, 0.06)",
          }}
        >
          <h1 style={{ marginTop: 0, fontSize: "1.4rem" }}>GreatOCR 启动失败</h1>
          <p style={{ marginBottom: 0, lineHeight: 1.7 }}>{message}</p>
        </div>
      </div>
    </StrictMode>,
  )
}
