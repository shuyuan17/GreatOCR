import { afterEach, describe, expect, it, vi } from "vitest"

import { apiFetch, uploadFile } from "./api"

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

  it("includes the page range when uploading a file", async () => {
    window.__GREAT_OCR_TOKEN__ = "session-token"
    const fetchMock = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          task: { task_id: "task-1" },
          file_path: "/tmp/sample.pdf",
          size_bytes: 123,
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    )

    await uploadFile(new File(["pdf"], "sample.pdf", { type: "application/pdf" }), {
      providerProfileId: "fake-default",
      pages: "1-3,5",
    })

    const [, init] = fetchMock.mock.calls[0]
    const body = init?.body
    expect(body).toBeInstanceOf(FormData)
    expect((body as FormData).get("pages")).toBe("1-3,5")
  })
})
