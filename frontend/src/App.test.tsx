import "@testing-library/jest-dom/vitest"
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
    provider_profile_id: "mineru-default",
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
    profile_id: "mineru-default",
    display_name: "MinerU",
    adapter_type: "mineru",
    endpoint: "https://mineru.net",
    model: null,
    public: true,
    capabilities: {},
    approved_fallback_ids: [],
    credential: { configured: true, masked: "********1234" },
  },
  {
    // 仅用于离线测试，UI 不应展示（fake-default）。
    profile_id: "fake-default",
    display_name: "Fake Provider",
    adapter_type: "fake",
    endpoint: null,
    model: null,
    public: false,
    capabilities: {},
    approved_fallback_ids: [],
    credential: { configured: false, masked: null },
  },
]

const apiModule = vi.hoisted(() => ({
  apiFetch: vi.fn(() => Promise.resolve(new Response(JSON.stringify({ status: "ok" })))),
  listProviders: vi.fn(() => Promise.resolve(providerList)),
  getPreferences: vi.fn(() => Promise.resolve({})),
  updatePreferences: vi.fn((prefs: Record<string, string>) => Promise.resolve(prefs)),
  updateProviderProfile: vi.fn((id: string) => Promise.resolve({ profile_id: id })),
  updateProviderCredential: vi.fn((id: string) => Promise.resolve({ profile_id: id })),
  testProviderConnection: vi.fn(() => Promise.resolve()),
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

    expect(await screen.findByText("结果")).toBeInTheDocument()
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

    // 结果链接应存在
    expect(await screen.findByText("结果")).toBeInTheDocument()
    // 质量报告因为不存在，不应有"报告"链接
    expect(screen.queryByText("报告")).not.toBeInTheDocument()
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

describe("New Task page - AI Processing UI", () => {
  beforeEach(() => {
    cleanup()
    vi.clearAllMocks()
    apiModule.listProviders.mockResolvedValue(providerList)
    apiModule.listTasks.mockResolvedValue([])
    apiModule.getDefaultOutputDir.mockResolvedValue({
      output_dir: "D:/repo/data/exports",
    })
  })

  function renderNewTask() {
    return render(
      <MemoryRouter initialEntries={["/new"]}>
        <App />
      </MemoryRouter>,
    )
  }

  it("shows the AI Processing title and subtitle", () => {
    renderNewTask()
    expect(screen.getByText("AI Processing")).toBeInTheDocument()
    expect(screen.getByText("OCR + AI 后处理工作流")).toBeInTheDocument()
  })

  it("shows the sensitive file option defaulting to 否", () => {
    renderNewTask()
    const sensitive = screen.getByLabelText("是否敏感文件？") as HTMLSelectElement
    expect(sensitive).toBeInTheDocument()
    // 默认：否
    expect(sensitive.value).toBe("no")
    expect(
      screen.getByText(
        "敏感文件会限制可用 Provider，避免发送到不合适的外部服务。",
      ),
    ).toBeInTheDocument()
  })

  it("shows AI Processing Mode defaulting to OCR Only", () => {
    renderNewTask()
    const mode = screen.getByLabelText("AI Processing Mode") as HTMLSelectElement
    expect(mode).toBeInTheDocument()
    // 默认：OCR Only
    expect(mode.value).toBe("ocr")
    expect(screen.getByText("OCR Only")).toBeInTheDocument()
    // OCR Only 说明文案
    expect(screen.getByText("仅执行 OCR，生成 result.docx")).toBeInTheDocument()
  })

  it("switches to Translation and reveals translation config", async () => {
    renderNewTask()
    const mode = screen.getByLabelText("AI Processing Mode") as HTMLSelectElement
    fireEvent.change(mode, { target: { value: "translation" } })
    expect(mode.value).toBe("translation")

    // Translation 配置仅在切换后出现
    const targetLanguage = (await screen.findByLabelText(
      "Target Language",
    )) as HTMLSelectElement
    expect(targetLanguage.value).toBe("Chinese")
    expect(screen.getByText("Chinese")).toBeInTheDocument()

    const translationMode = screen.getByLabelText(
      "Translation Mode",
    ) as HTMLSelectElement
    expect(translationMode.value).toBe("Page by Page")
    expect(screen.getByText("Page by Page")).toBeInTheDocument()

    // Page by Page 使用 OCR 页码范围的提示
    expect(
      screen.getByText(/Page by Page 会使用 OCR 时选择的页码范围/),
    ).toBeInTheDocument()

    // Translation 说明文案
    expect(
      screen.getByText("OCR 完成后执行 AI 翻译，生成 translated_result.docx"),
    ).toBeInTheDocument()
  })

  it("shows Current Workflow with OCR provider and Not used for translation in OCR Only mode", async () => {
    renderNewTask()
    expect(await screen.findByText("Current Workflow")).toBeInTheDocument()
    expect(screen.getByText(/OCR Provider: MinerU/)).toBeInTheDocument()
    // OCR Only 默认：Translation Provider = Not used
    expect(screen.getByText(/Not used/)).toBeInTheDocument()
    expect(screen.getByText(/Providers are configured in/)).toBeInTheDocument()
  })

  it("shows DeepSeek as Translation Provider when Translation mode is selected", async () => {
    renderNewTask()
    const mode = screen.getByLabelText("AI Processing Mode") as HTMLSelectElement
    fireEvent.change(mode, { target: { value: "translation" } })
    expect(await screen.findByText(/Translation Provider: DeepSeek/)).toBeInTheDocument()
    // 切换到 Translation 后，不应再显示 Not used
    expect(screen.queryByText(/Not used/)).not.toBeInTheDocument()
  })

  it("changes the submit button label with the AI mode", async () => {
    renderNewTask()
    expect(
      screen.getByRole("button", { name: "开始 OCR" }),
    ).toBeInTheDocument()

    const mode = screen.getByLabelText("AI Processing Mode") as HTMLSelectElement
    fireEvent.change(mode, { target: { value: "translation" } })

    expect(
      screen.getByRole("button", { name: "开始 OCR + 翻译" }),
    ).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "开始 OCR" })).toBeNull()
  })
})

describe("Settings page - AI Provider Library & Default Workflow", () => {
  beforeEach(() => {
    cleanup()
    vi.clearAllMocks()
    apiModule.listProviders.mockResolvedValue(providerList)
    apiModule.listTasks.mockResolvedValue([])
    apiModule.getPreferences.mockResolvedValue({})
    apiModule.getDefaultOutputDir.mockResolvedValue({
      output_dir: "D:/repo/data/exports",
    })
  })

  function renderSettings() {
    return render(
      <MemoryRouter initialEntries={["/settings"]}>
        <App />
      </MemoryRouter>,
    )
  }

  it("shows the AI Provider Library section", async () => {
    renderSettings()
    expect(await screen.findByText(/AI Provider Library/)).toBeInTheDocument()
  })

  it("shows the MinerU provider", async () => {
    renderSettings()
    expect((await screen.findAllByText("MinerU")).length).toBeGreaterThan(0)
  })

  it("shows the DeepSeek provider", async () => {
    renderSettings()
    expect((await screen.findAllByText("DeepSeek")).length).toBeGreaterThan(0)
  })

  it("does not show the Fake Provider", async () => {
    renderSettings()
    // fake-default 应被过滤，正式 UI 不展示。
    expect(await screen.findByText(/AI Provider Library/)).toBeInTheDocument()
    expect(screen.queryByText("Fake Provider")).not.toBeInTheDocument()
  })

  it("shows the Capabilities label", async () => {
    renderSettings()
    expect((await screen.findAllByText("Capabilities:")).length).toBeGreaterThan(0)
    // 能力标签至少包含 OCR / Translation
    expect(screen.getAllByText("OCR").length).toBeGreaterThan(0)
    expect(screen.getAllByText("Translation").length).toBeGreaterThan(0)
  })

  it("shows Sensitive File Not Allowed", async () => {
    renderSettings()
    expect((await screen.findAllByText("Sensitive File:")).length).toBeGreaterThan(0)
    expect(screen.getAllByText("Not Allowed").length).toBeGreaterThan(0)
  })

  it("shows the Default Workflow Configuration section", async () => {
    renderSettings()
    expect(await screen.findByText(/Default Workflow Configuration/)).toBeInTheDocument()
    expect(screen.getByText("Default OCR Provider")).toBeInTheDocument()
    expect(screen.getByText("Default Translation Provider")).toBeInTheDocument()
    expect(screen.getByText(/New Task page will use these defaults/)).toBeInTheDocument()
  })

  it("shows the Add AI Provider button", async () => {
    renderSettings()
    expect(
      await screen.findByRole("button", { name: "+ Add AI Provider" }),
    ).toBeInTheDocument()
  })

  it("shows the V2.4 notice when Add AI Provider is clicked", async () => {
    renderSettings()
    const addButton = await screen.findByRole("button", { name: "+ Add AI Provider" })
    fireEvent.click(addButton)
    expect(
      await screen.findByText("AI Provider management will be available in V2.4."),
    ).toBeInTheDocument()
  })

  it("shows coming soon providers as disabled cards", async () => {
    renderSettings()
    expect(await screen.findByText("OpenAI")).toBeInTheDocument()
    expect(screen.getByText("Azure Document Intelligence")).toBeInTheDocument()
    expect(screen.getByText("Local Model")).toBeInTheDocument()
    // Local Model 允许敏感文件
    expect(screen.getAllByText("Allowed").length).toBeGreaterThan(0)
  })
})
