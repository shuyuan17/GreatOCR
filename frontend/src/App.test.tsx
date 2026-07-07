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
    completed_at: "2026-07-04T12:30:00+00:00",
    processing_mode: "ocr",
    ocr_provider_profile_id: "mineru-default",
    translation_provider_profile_id: null,
    target_language: null,
    translation_mode: null,
    created_at: "2026-07-04T12:00:00+00:00",
    ...overrides,
  }
}

function makeResultSummary(
  overrides: {
    task?: Record<string, unknown>
    resultExists?: boolean
    qualityExists?: boolean
    translatedExists?: boolean
    errorMessage?: string | null
    resultFilename?: string
    qualityFilename?: string
    translatedFilename?: string
  } = {},
) {
  const resultExists = overrides.resultExists ?? true
  const qualityExists = overrides.qualityExists ?? true
  const translatedExists = overrides.translatedExists ?? false
  const task = makeTask(overrides.task ?? {})

  return {
    task,
    error_message: overrides.errorMessage ?? null,
    files: {
      result_docx: {
        key: "result_docx",
        filename: overrides.resultFilename ?? "sample.docx",
        exists: resultExists,
        download_path: resultExists
          ? `/api/tasks/${task.task_id}/download/${overrides.resultFilename ?? "sample.docx"}`
          : null,
      },
      quality_report_docx: {
        key: "quality_report_docx",
        filename: overrides.qualityFilename ?? "quality-report.docx",
        exists: qualityExists,
        download_path: qualityExists
          ? `/api/tasks/${task.task_id}/download/quality-report.docx`
          : null,
      },
      translated_docx: {
        key: "translated_docx",
        filename: overrides.translatedFilename ?? "sample_翻译.docx",
        exists: translatedExists,
        download_path: translatedExists
          ? `/api/tasks/${task.task_id}/download/${overrides.translatedFilename ?? "sample_翻译.docx"}`
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
    profile_id: "zhipu-glm-default",
    display_name: "智谱 GLM",
    adapter_type: "openai-compatible",
    endpoint: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    model: "glm-4-plus",
    public: true,
    capabilities: { translation: true, text_processing: true },
    approved_fallback_ids: [],
    credential: { configured: true, masked: "********5678" },
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
    localStorage.clear()
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

    await screen.findByLabelText("选择文件")

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

    expect(await screen.findByText("sample.docx")).toBeInTheDocument()
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

    // OCR 结果链接应存在
    expect(await screen.findByText("sample.docx")).toBeInTheDocument()
    // 质量报告因为不存在，不应有质量报告文件链接
    expect(screen.queryByText("quality-report.docx")).not.toBeInTheDocument()
  })

  it("shows a safe translation failure reason for partial tasks", async () => {
    apiModule.listTasks.mockResolvedValue([
      makeTask({ task_id: "task-3", status: "partial" }),
    ])
    apiModule.getTaskResultFiles.mockResolvedValue(
      makeResultSummary({
        task: { task_id: "task-3", status: "partial" },
        resultExists: true,
        translatedExists: false,
        errorMessage:
          "Translation Provider authentication failed. Please check API Key configuration.",
      }),
    )

    render(
      <MemoryRouter initialEntries={["/tasks?task=task-3"]}>
        <App />
      </MemoryRouter>,
    )

    expect(
      await screen.findByText(
        "Translation Provider authentication failed. Please check API Key configuration.",
      ),
    ).toBeInTheDocument()
  })

  it("does not show an error reason for succeeded tasks", async () => {
    apiModule.listTasks.mockResolvedValue([
      makeTask({ task_id: "task-4", status: "succeeded" }),
    ])
    apiModule.getTaskResultFiles.mockResolvedValue(
      makeResultSummary({
        task: { task_id: "task-4", status: "succeeded" },
        errorMessage:
          "Translation Provider authentication failed. Please check API Key configuration.",
      }),
    )

    render(
      <MemoryRouter initialEntries={["/tasks?task=task-4"]}>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText("sample.docx")
    expect(
      screen.queryByText(
        "Translation Provider authentication failed. Please check API Key configuration.",
      ),
    ).not.toBeInTheDocument()
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

describe("Settings page - AI Provider 库 & 默认工作流配置", () => {
  beforeEach(() => {
    cleanup()
    localStorage.clear()
    vi.clearAllMocks()
    apiModule.listProviders.mockResolvedValue(providerList)
    apiModule.listTasks.mockResolvedValue([])
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

  it("shows 一、AI Provider 库", async () => {
    renderSettings()
    expect(await screen.findByText("一、AI Provider 库")).toBeInTheDocument()
  })

  it("shows 二、默认工作流配置", async () => {
    renderSettings()
    expect(await screen.findByText("二、默认工作流配置")).toBeInTheDocument()
  })

  it("default OCR Provider is a dropdown", async () => {
    renderSettings()
    const select = (await screen.findByLabelText(
      "默认 OCR Provider",
    )) as HTMLSelectElement
    expect(select.tagName).toBe("SELECT")
  })

  it("default OCR Provider dropdown only lists OCR-capable providers", async () => {
    renderSettings()
    const select = (await screen.findByLabelText(
      "默认 OCR Provider",
    )) as HTMLSelectElement
    const optionTexts = Array.from(select.options).map((o) => o.textContent)
    // MinerU 具备 OCR 能力；DeepSeek / coming soon 的 Provider 不应出现。
    expect(optionTexts).toEqual(["MinerU"])
    expect(optionTexts).not.toContain("DeepSeek")
    expect(optionTexts).not.toContain("智谱 GLM")
    expect(optionTexts).not.toContain("Azure Document Intelligence")
  })

  it("default translation Provider is a dropdown", async () => {
    renderSettings()
    const select = (await screen.findByLabelText(
      "默认翻译 Provider",
    )) as HTMLSelectElement
    expect(select.tagName).toBe("SELECT")
  })

  it("default translation Provider dropdown only lists Translation-capable providers", async () => {
    renderSettings()
    const select = (await screen.findByLabelText(
      "默认翻译 Provider",
    )) as HTMLSelectElement
    const optionTexts = Array.from(select.options).map((o) => o.textContent)
    // DeepSeek 具备 Translation 能力；MinerU / coming soon 的 Provider 不应出现。
    expect(optionTexts).toEqual(["DeepSeek", "智谱 GLM"])
    expect(optionTexts).not.toContain("MinerU")
  })

  it("persists default workflow config to localStorage when changed", async () => {
    renderSettings()
    const ocrSelect = (await screen.findByLabelText(
      "默认 OCR Provider",
    )) as HTMLSelectElement
    const transSelect = screen.getByLabelText(
      "默认翻译 Provider",
    ) as HTMLSelectElement

    fireEvent.change(ocrSelect, { target: { value: "mineru" } })
    fireEvent.change(transSelect, { target: { value: "deepseek" } })

    const stored = JSON.parse(
      localStorage.getItem("greatocr.workflowConfig") || "{}",
    )
    expect(stored.ocrProviderId).toBe("mineru")
    expect(stored.translationProviderId).toBe("deepseek")
  })
})

describe("New Task page - AI Processing workflow", () => {
  beforeEach(() => {
    cleanup()
    localStorage.clear()
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

  function selectPdf() {
    fireEvent.change(screen.getByLabelText("选择文件"), {
      target: {
        files: [new File(["pdf"], "sample.pdf", { type: "application/pdf" })],
      },
    })
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

  it("shows Processing Mode defaulting to OCR Only", () => {
    renderNewTask()
    const mode = screen.getByLabelText("Processing Mode") as HTMLSelectElement
    expect(mode).toBeInTheDocument()
    // 默认：OCR Only
    expect(mode.value).toBe("ocr")
    expect(screen.getByText("OCR Only")).toBeInTheDocument()
    // OCR Only 说明文案
    expect(screen.getByText("仅执行 OCR，生成 OCR 结果文档")).toBeInTheDocument()
  })

  it("switches to OCR + Translation and reveals translation config", async () => {
    renderNewTask()
    const mode = screen.getByLabelText("Processing Mode") as HTMLSelectElement
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
      screen.getByText("OCR 完成后执行 AI 翻译，生成翻译结果文档"),
    ).toBeInTheDocument()
  })

  it("shows 当前工作流 section", () => {
    renderNewTask()
    expect(screen.getByText("当前工作流")).toBeInTheDocument()
    expect(screen.getByText(/OCR Provider：MinerU/)).toBeInTheDocument()
  })

  it("OCR Only shows 未启用 for Translation Provider", () => {
    renderNewTask()
    // 默认 OCR Only：Translation Provider 显示 未启用
    expect(screen.getByText(/未启用/)).toBeInTheDocument()
    expect(screen.queryByText(/DeepSeek/)).not.toBeInTheDocument()
  })

  it("OCR + Translation shows DeepSeek for Translation Provider", async () => {
    renderNewTask()
    const mode = screen.getByLabelText("Processing Mode") as HTMLSelectElement
    fireEvent.change(mode, { target: { value: "translation" } })
    expect(await screen.findByText(/DeepSeek/)).toBeInTheDocument()
    // 切换到 OCR + Translation 后，不应再显示 未启用
    expect(screen.queryByText(/未启用/)).not.toBeInTheDocument()
  })

  it("reflects a saved 智谱 GLM translation provider in Current Workflow", async () => {
    localStorage.setItem(
      "greatocr.workflowConfig",
      JSON.stringify({
        ocrProviderId: "mineru",
        translationProviderId: "zhipu-glm",
      }),
    )
    renderNewTask()
    const mode = screen.getByLabelText("Processing Mode") as HTMLSelectElement
    fireEvent.change(mode, { target: { value: "translation" } })

    expect(await screen.findByText(/Translation Provider：智谱 GLM/)).toBeInTheDocument()
  })

  it("shows warning and disables submit when sensitive file = 是 with disallowed providers", async () => {
    renderNewTask()
    selectPdf()
    // 等待 Provider 加载完成，默认（敏感文件=否）按钮可用，证明禁用来自敏感校验
    await waitFor(() => {
      const btn = screen.getByRole("button", {
        name: "开始 OCR",
      }) as HTMLButtonElement
      expect(btn.disabled).toBe(false)
    })

    const sensitive = screen.getByLabelText("是否敏感文件？") as HTMLSelectElement
    fireEvent.change(sensitive, { target: { value: "yes" } })

    // 默认 Provider（MinerU / DeepSeek）均不允许敏感文件，应显示警告并禁用按钮
    expect(
      screen.getByText(
        /当前工作流包含不允许处理敏感文件的 AI Provider/,
      ),
    ).toBeInTheDocument()

    const submit = screen.getByRole("button", {
      name: "开始 OCR",
    }) as HTMLButtonElement
    expect(submit.disabled).toBe(true)

    // 切回“否”后恢复可用
    fireEvent.change(sensitive, { target: { value: "no" } })
    expect(submit.disabled).toBe(false)
  })

  it("OCR + Translation shows public filenames in Output Preview", async () => {
    renderNewTask()
    const mode = screen.getByLabelText("Processing Mode") as HTMLSelectElement
    fireEvent.change(screen.getByLabelText("选择文件"), {
      target: {
        files: [new File(["pdf"], "英文签字盖章有页眉的.pdf", { type: "application/pdf" })],
      },
    })
    fireEvent.change(mode, { target: { value: "translation" } })
    expect(await screen.findByText("英文签字盖章有页眉的_翻译.docx")).toBeInTheDocument()
    expect(screen.getByText("英文签字盖章有页眉的.docx")).toBeInTheDocument()
  })

  it("shows public filenames in task center download titles", async () => {
    apiModule.listTasks.mockResolvedValue([
      makeTask({ task_id: "task-5", display_name: "contract.pdf", status: "succeeded" }),
    ])
    apiModule.getTaskResultFiles.mockResolvedValue(
      makeResultSummary({
        task: { task_id: "task-5", display_name: "contract.pdf", status: "succeeded" },
        resultFilename: "contract.docx",
        translatedFilename: "contract_翻译.docx",
        translatedExists: true,
      }),
    )

    render(
      <MemoryRouter initialEntries={["/tasks?task=task-5"]}>
        <App />
      </MemoryRouter>,
    )

    await screen.findByText("contract.docx")
    expect(screen.getByRole("link", { name: "contract.docx" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "contract_翻译.docx" })).toBeInTheDocument()
  })

  it("changes the submit button label with the AI mode", async () => {
    renderNewTask()
    expect(
      screen.getByRole("button", { name: "开始 OCR" }),
    ).toBeInTheDocument()

    const mode = screen.getByLabelText("Processing Mode") as HTMLSelectElement
    fireEvent.change(mode, { target: { value: "translation" } })

    expect(
      screen.getByRole("button", { name: "开始 OCR + 翻译" }),
    ).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "开始 OCR" })).toBeNull()
  })

  it("starts a task using the OCR Provider from saved config (not listProviders()[0])", async () => {
    // 后端返回的第一个 Provider 是 fake-default，证明新建任务页不使用后端列表第一个。
    apiModule.listProviders.mockResolvedValue([
      {
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
    ])
    apiModule.uploadFile.mockResolvedValue({
      task: makeTask({ task_id: "task-x", status: "paused" }),
      file_path: "x",
      size_bytes: 10,
    })
    apiModule.startTask.mockResolvedValue(
      makeTask({ task_id: "task-x", status: "running" }),
    )
    apiModule.getTask.mockResolvedValue(
      makeTask({ task_id: "task-x", status: "succeeded" }),
    )

    // 默认配置：ocr=mineru（profileId=mineru-default）
    localStorage.setItem(
      "greatocr.workflowConfig",
      JSON.stringify({ ocrProviderId: "mineru", translationProviderId: "deepseek" }),
    )
    renderNewTask()
    // Current Workflow 显示 MinerU（来自配置，而非后端 fake-default）
    expect(await screen.findByText(/OCR Provider：MinerU/)).toBeInTheDocument()

    selectPdf()
    fireEvent.click(screen.getByRole("button", { name: "开始 OCR" }))

    await waitFor(() => {
      expect(apiModule.uploadFile).toHaveBeenCalledWith(
        expect.any(File),
        expect.objectContaining({ providerProfileId: "mineru-default" }),
      )
    })
    // 明确不应使用后端列表的第一个 Provider
    expect(apiModule.uploadFile).not.toHaveBeenCalledWith(
      expect.any(File),
      expect.objectContaining({ providerProfileId: "fake-default" }),
    )
  })

  it("reflects a non-default saved OCR Provider in Current Workflow", async () => {
    // 选择 azure-doc-intel（catalog 中具备 OCR 能力的 Provider，非 MinerU），
    // 证明新建任务页读取保存的配置而非写死 MinerU。
    localStorage.setItem(
      "greatocr.workflowConfig",
      JSON.stringify({
        ocrProviderId: "azure-doc-intel",
        translationProviderId: "deepseek",
      }),
    )
    renderNewTask()
    expect(
      await screen.findByText(/OCR Provider：Azure Document Intelligence/),
    ).toBeInTheDocument()
  })
})

describe("Settings page - AI Provider Library & Default Workflow", () => {
  beforeEach(() => {
    cleanup()
    localStorage.clear()
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
    expect(await screen.findByText("一、AI Provider 库")).toBeInTheDocument()
  })

  it("shows the MinerU provider", async () => {
    renderSettings()
    expect((await screen.findAllByText("MinerU")).length).toBeGreaterThan(0)
  })

  it("shows the DeepSeek provider", async () => {
    renderSettings()
    expect((await screen.findAllByText("DeepSeek")).length).toBeGreaterThan(0)
  })

  it("shows the 智谱 GLM provider", async () => {
    renderSettings()
    expect((await screen.findAllByText("智谱 GLM")).length).toBeGreaterThan(0)
  })

  it("does not show the Fake Provider", async () => {
    renderSettings()
    // fake-default 应被过滤，正式 UI 不展示。
    expect(await screen.findByText("一、AI Provider 库")).toBeInTheDocument()
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
    expect(await screen.findByText("二、默认工作流配置")).toBeInTheDocument()
    expect(screen.getByLabelText("默认 OCR Provider")).toBeInTheDocument()
    expect(screen.getByLabelText("默认翻译 Provider")).toBeInTheDocument()
    expect(
      screen.getByText(/新建任务页会使用这里选择的默认 Provider/),
    ).toBeInTheDocument()
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
