import { afterEach, describe, expect, it, vi } from "vitest"

import { apiFetch } from "./api"

declare global {
  interface Window {
    __GREAT_OCR_TOKEN__: string
  }
}

describe("apiFetch", () => {
  afterEach(() => vi.restoreAllMocks())

  it("adds the current session token without mutating caller headers", async () => {
    window.__GREAT_OCR_TOKEN__ = "session-token"
    const fetchMock = vi.spyOn(window, "fetch").mockResolvedValue(new Response())
    const headers = new Headers({ Accept: "application/json" })

    await apiFetch("/health", { headers })

    const [, init] = fetchMock.mock.calls[0]
    const sent = new Headers(init?.headers)
    expect(sent.get("X-GreatOCR-Token")).toBe("session-token")
    expect(headers.has("X-GreatOCR-Token")).toBe(false)
  })
})
