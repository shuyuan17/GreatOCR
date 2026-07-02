/// <reference types="vite/client" />

declare global {
  interface Window {
    __GREAT_OCR_TOKEN__: string
  }
}

const API_BASE = "/api"

/**
 * Fetch wrapper that prepends `/api` and injects the session token header.
 *
 * - Never mutates the caller's `headers` object.
 * - In development, the request is proxied by Vite to the backend server.
 */
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
