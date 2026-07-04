import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { App } from "./App"

function makeTask(overrides: Record<string, unknown> = {}) {
  return {
    task_id: "task-1",
    display_name: "sample.pdf",
    source_path: "C:/docs/sample.pdf",
    sensitive: false,
    selected_pages: [1, 2, 3],
    provider_profile_id: "fake-default",
    approved_fallback_ids: [],
    status: "succeeded",
    output_dir: "C:/output/task-1",
    quality_rating: "high",
    requested_action: null,
    created_at: "2026-07-04T12:00:00+00:00",
    ...overrides,
  }
}

function makeResultSummary(
  overrides: {
    task?: Record<string, unknown>
    resultExists?: boolean
    qualityExists?: boolean
  } = {},
) {
  const resultExists = overrides.resultExists ?? true
  const qualityExists = overrides.qualityExists ?? true
  const task = makeTask(overrides.task ?? {})

  return {
    task,
    files: {
      result_docx: {
        key: "result_docx",
        filename: "result.docx",
        exists: resultExists,
        download_path: resultExists
          ? `/api/tasks/${task.task_id}/download/result.docx`
          : null,
      },
      quality_report_docx: {
        key: "quality_report_docx",
        filename: "quality-report.docx",
        exists: qualityExists,
        download_path: qualityExists
          ? `/api/tasks/${task.task_id}/download/quality-report.docx`
          : null,
      },
    },
  }
}

const providerList = [
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
]

const apiModule = vi.hoisted(() => ({
  apiFetch: vi.fn(() => Promise.resolve(new Response(JSON.stringify({ status: "ok" })))),
  listProviders: vi.fn(() => Promise.resolve(providerList)),
  uploadFile: vi.fn(),
  startTask: vi.fn(),
  getTask: vi.fn(),
  listTasks: vi.fn(() => Promise.resolve([])),
  getTaskResultFiles: vi.fn(),
  getDefaultOutputDir: vi.fn(() =>
    Promise.resolve({ output_dir: "D:/repo/data/exports" }),
  ),
}))

vi.mock("./api", () => apiModule)

describe("GreatOCR application shell", () => {
  beforeEach(() => {
    cleanup()
    vi.clearAllMocks()
    apiModule.listProviders.mockResolvedValue(providerList)
    apiModule.listTasks.mockResolvedValue([])
    apiModule.getDefaultOutputDir.mockResolvedValue({
      output_dir: "D:/repo/data/exports",
    })
  })

  it("renders the primary navigation", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText("GreatOCR")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "任务中心" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "新建任务" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "设置" })).toBeInTheDocument()
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

    fireEvent.change(screen.getByLabelText("选择文件"), {
      target: {
        files: [new File(["pdf"], "sample.pdf", { type: "application/pdf" })],
      },
    })
    fireEvent.change(screen.getByLabelText("页码范围"), {
      target: { value: "3-1" },
    })
    fireEvent.click(screen.getByRole("button", { name: "开始 OCR" }))

    expect(
      await screen.findByText((content) => content.includes("页码范围格式不正确")),
    ).toBeInTheDocument()
    expect(apiModule.uploadFile).not.toHaveBeenCalled()
  })

  it("expands the current finished task in task center", async () => {
    apiModule.listTasks.mockResolvedValue([
      makeTask({ task_id: "task-1", status: "succeeded" }),
    ])
    apiModule.getTaskResultFiles.mockResolvedValue(
      makeResultSummary({
        task: { task_id: "task-1", status: "succeeded" },
        resultExists: true,
        qualityExists: true,
      }),
    )

    render(
      <MemoryRouter initialEntries={["/tasks?task=task-1"]}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByRole("link", { name: "下载 result.docx" })).toBeInTheDocument()
  })

  it("shows a friendly message when quality report is missing", async () => {
    apiModule.listTasks.mockResolvedValue([
      makeTask({ task_id: "task-2", status: "succeeded" }),
    ])
    apiModule.getTaskResultFiles.mockResolvedValue(
      makeResultSummary({
        task: { task_id: "task-2", status: "succeeded" },
        resultExists: true,
        qualityExists: false,
      }),
    )

    render(
      <MemoryRouter initialEntries={["/tasks?task=task-2"]}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText("本次未生成质量报告")).toBeInTheDocument()
  })

  it("loads the default output path on the new task page", async () => {
    render(
      <MemoryRouter initialEntries={["/new"]}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByDisplayValue("D:/repo/data/exports")).toBeInTheDocument()
  })

  it("submits a custom output path with the upload request", async () => {
    apiModule.uploadFile.mockResolvedValue({
      task: makeTask({ task_id: "task-3", status: "paused" }),
      file_path: "x",
      size_bytes: 10,
    })
    apiModule.startTask.mockResolvedValue(
      makeTask({ task_id: "task-3", status: "running" }),
    )
    apiModule.getTask.mockResolvedValue(
      makeTask({ task_id: "task-3", status: "succeeded" }),
    )

    render(
      <MemoryRouter initialEntries={["/new"]}>
        <App />
      </MemoryRouter>,
    )

    fireEvent.change(screen.getAllByLabelText("选择文件")[0], {
      target: {
        files: [new File(["pdf"], "sample.pdf", { type: "application/pdf" })],
      },
    })
    fireEvent.change(await screen.findByDisplayValue("D:/repo/data/exports"), {
      target: { value: "D:/custom-output" },
    })
    fireEvent.click(screen.getByRole("button", { name: "开始 OCR" }))

    await waitFor(() => {
      expect(apiModule.uploadFile).toHaveBeenCalledWith(
        expect.any(File),
        expect.objectContaining({ outputDir: "D:/custom-output" }),
      )
    })
  })

  it("shows the newest task first in task center", async () => {
    apiModule.listTasks.mockResolvedValue([
      makeTask({
        task_id: "older",
        display_name: "older.pdf",
        created_at: "2026-07-04T10:00:00+00:00",
      }),
      makeTask({
        task_id: "newer",
        display_name: "newer.pdf",
        created_at: "2026-07-04T11:00:00+00:00",
      }),
    ])

    render(
      <MemoryRouter initialEntries={["/tasks"]}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText("newer.pdf")).toBeInTheDocument()
    const taskNames = screen.getAllByText(/\.pdf$/)
    expect(taskNames[0]).toHaveTextContent("newer.pdf")
    expect(taskNames[1]).toHaveTextContent("older.pdf")
  })
})
