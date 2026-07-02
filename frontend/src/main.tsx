import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"

import { App } from "./App"

/* ------------------------------------------------------------------ */
/*  Session token setup                                                */
/* ------------------------------------------------------------------ */

const TOKEN_FROM_ENV = import.meta.env.VITE_GREAT_OCR_TOKEN

/**
 * Use the token from env (`.env.development`) if set, otherwise generate
 * a random hex token.  The backend must be started with the same token.
 */
window.__GREAT_OCR_TOKEN__ =
  TOKEN_FROM_ENV || generateSessionToken()

function generateSessionToken(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  const token = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")
  console.log(
    "%c[GreatOCR] Generated session token (set VITE_GREAT_OCR_TOKEN to use a fixed one):",
    "color: #1565c0; font-weight: bold",
  )
  console.log(`  %c${token}`, "color: #2e7d32; font-weight: bold")
  return token
}

/* ------------------------------------------------------------------ */
/*  Render                                                             */
/* ------------------------------------------------------------------ */

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
