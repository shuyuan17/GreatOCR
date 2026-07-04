import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { App } from "./App"

const apiModule = vi.hoisted(() => ({
  apiFetch: vi.fn(() => Promise.resolve(new Response(JSON.stringify({ status: "ok" })))),
  listProviders: vi.fn(() =>
    Promise.resolve([
      {
        profile_id: "fake-default",
        display_name: "Fake Provider",
        adapter_type: "fake",
        endpoint: null,
        public: false,
        capabilities: {},
        approved_fallback_ids: [],
        credential: { configured: true, masked: null },
      },
    ]),
  ),
  uploadFile: vi.fn(),
  startTask: vi.fn(),
  getTask: vi.fn(),
}))

vi.mock("./api", () => apiModule)

describe("GreatOCR application shell", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("renders the primary navigation", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText("任务中心")).toBeInTheDocument()
    expect(screen.getByText("新建任务")).toBeInTheDocument()
    expect(screen.getByText("设置")).toBeInTheDocument()
  })

  it("shows an error instead of uploading an invalid page range", async () => {
    render(
      <MemoryRouter initialEntries={["/new"]}>
        <App />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(apiModule.listProviders).toHaveBeenCalled()
    })

    fireEvent.change(screen.getByLabelText("选择文件（图片或 PDF）"), {
      target: {
        files: [new File(["pdf"], "sample.pdf", { type: "application/pdf" })],
      },
    })
    fireEvent.change(screen.getByLabelText("页码范围"), {
      target: { value: "3-1" },
    })
    fireEvent.click(screen.getByRole("button", { name: "开始 OCR" }))

    expect(await screen.findByText(/页码范围格式不正确/)).toBeInTheDocument()
    expect(apiModule.uploadFile).not.toHaveBeenCalled()
  })
})
