// AI Processing 配置常量。
// 集中管理，方便以后新增语言、翻译模式、处理模式，而无需改动新建任务页 UI 逻辑。

export type SensitiveValue = "no" | "yes"
export type AiModeValue = "ocr" | "translation"

export interface Option<T extends string> {
  value: T
  label: string
  description?: string
}

// 是否敏感文件（任务级选项，本任务只做前端 UI 状态，不传后端）。
export const SENSITIVE_OPTIONS: Option<SensitiveValue>[] = [
  { value: "no", label: "否" },
  { value: "yes", label: "是" },
]
export const DEFAULT_SENSITIVE: SensitiveValue = "no"

// AI Processing Mode（UI 展示用，本任务不接后端）。
export const AI_PROCESSING_MODES: Option<AiModeValue>[] = [
  {
    value: "ocr",
    label: "OCR Only",
    description: "仅执行 OCR，生成 result.docx",
  },
  {
    value: "translation",
    label: "OCR + Translation",
    description: "OCR 完成后执行 AI 翻译，生成 translated_result.docx",
  },
]
export const DEFAULT_AI_MODE: AiModeValue = "ocr"

// 翻译目标语言（当前仅 Chinese，使用常量数组方便以后扩展）。
export const TARGET_LANGUAGES = ["Chinese"] as const
export type TargetLanguage = (typeof TARGET_LANGUAGES)[number]
export const DEFAULT_TARGET_LANGUAGE: TargetLanguage = TARGET_LANGUAGES[0]

// 翻译模式（当前仅 Page by Page，使用常量数组方便以后扩展）。
export const TRANSLATION_MODES = ["Page by Page"] as const
export type TranslationMode = (typeof TRANSLATION_MODES)[number]
export const DEFAULT_TRANSLATION_MODE: TranslationMode = TRANSLATION_MODES[0]

// 默认展示名称（仅在目录查找失败时作为兜底，正常从 AI_PROVIDER_CATALOG 派生）。
export const DEFAULT_OCR_PROVIDER = "MinerU"
export const DEFAULT_TRANSLATION_PROVIDER = "DeepSeek"

// ---------------------------------------------------------------------------
// AI Provider 概念（UI 设计层目录，本任务只做 UI，不接后端 / 不写库）
// ---------------------------------------------------------------------------

// AI Provider 能力标签。
export type ProviderCapability =
  | "OCR"
  | "Translation"
  | "Summary"
  | "Formatting"
  | "Text Processing"

// AI Provider 目录：Settings 页「AI Provider 库」与新建任务页「当前工作流」的统一数据源。
// - 真实可配置的 Provider（MinerU / DeepSeek）标记为 active。
// - 计划中的 Provider 标记为 comingSoon（disabled 卡片，不可配置、不可选为默认）。
// - fake-default 仅用于离线测试，不进入此目录，正式 UI 不展示。
export interface AiProviderCatalogEntry {
  id: string
  profileId: string
  displayName: string
  capabilities: ProviderCapability[]
  sensitiveAllowed: boolean
  comingSoon?: boolean
  status?: "active" | "comingSoon"
}

export const AI_PROVIDER_CATALOG: AiProviderCatalogEntry[] = [
  {
    id: "mineru",
    profileId: "mineru-default",
    displayName: "MinerU",
    capabilities: ["OCR"],
    sensitiveAllowed: false,
    status: "active",
  },
  {
    id: "deepseek",
    profileId: "deepseek-default",
    displayName: "DeepSeek",
    capabilities: ["Translation", "Text Processing"],
    sensitiveAllowed: false,
    status: "active",
  },
  // ---- Coming Soon（disabled 卡片，V2.4 起可用）----
  {
    id: "openai",
    profileId: "openai",
    displayName: "OpenAI",
    capabilities: ["Translation", "Summary", "Formatting"],
    sensitiveAllowed: false,
    comingSoon: true,
    status: "comingSoon",
  },
  {
    id: "azure-doc-intel",
    profileId: "azure-doc-intel",
    displayName: "Azure Document Intelligence",
    capabilities: ["OCR"],
    sensitiveAllowed: false,
    comingSoon: true,
    status: "comingSoon",
  },
  {
    id: "local-model",
    profileId: "local-model",
    displayName: "Local Model",
    capabilities: ["OCR", "Translation"],
    sensitiveAllowed: true,
    comingSoon: true,
    status: "comingSoon",
  },
]

// 按目录 id 查找 Provider。
export function getProviderById(id: string): AiProviderCatalogEntry | undefined {
  return AI_PROVIDER_CATALOG.find((provider) => provider.id === id)
}

// 默认 OCR Provider 下拉选项：具备 OCR 能力且已上线（非 comingSoon）的 Provider。
export function getOcrProviderOptions(): AiProviderCatalogEntry[] {
  return AI_PROVIDER_CATALOG.filter(
    (provider) => !provider.comingSoon && provider.capabilities.includes("OCR"),
  )
}

// 默认翻译 Provider 下拉选项：具备 Translation 能力且已上线（非 comingSoon）的 Provider。
export function getTranslationProviderOptions(): AiProviderCatalogEntry[] {
  return AI_PROVIDER_CATALOG.filter(
    (provider) =>
      !provider.comingSoon && provider.capabilities.includes("Translation"),
  )
}

// 默认工作流配置（UI 展示与提交用的前端默认值）。
// 新建任务页与设置页共用，保证“当前工作流”与默认 Provider 下拉一致。
export const DEFAULT_WORKFLOW_CONFIG: {
  ocrProviderId: string
  translationProviderId: string
} = {
  ocrProviderId: "mineru",
  translationProviderId: "deepseek",
}

// ---------------------------------------------------------------------------
// 默认工作流配置持久化（仅前端 localStorage，不写后端 / 不连数据库）
// ---------------------------------------------------------------------------

const WORKFLOW_CONFIG_STORAGE_KEY = "greatocr.workflowConfig"

export interface WorkflowConfig {
  ocrProviderId: string
  translationProviderId: string
}

// 读取保存的默认工作流配置：localStorage 优先，缺失 / 损坏 / 非法 id 时回退默认值。
// 仅前端状态，不影响后端 Provider 列表。
export function loadWorkflowConfig(): WorkflowConfig {
  const fallback: WorkflowConfig = {
    ocrProviderId: DEFAULT_WORKFLOW_CONFIG.ocrProviderId,
    translationProviderId: DEFAULT_WORKFLOW_CONFIG.translationProviderId,
  }
  try {
    const raw = localStorage.getItem(WORKFLOW_CONFIG_STORAGE_KEY)
    if (!raw) return fallback
    const parsed = JSON.parse(raw) as Partial<WorkflowConfig>
    const ocrId = parsed.ocrProviderId
    const transId = parsed.translationProviderId
    return {
      ocrProviderId:
        ocrId && getProviderById(ocrId) ? ocrId : fallback.ocrProviderId,
      translationProviderId:
        transId && getProviderById(transId)
          ? transId
          : fallback.translationProviderId,
    }
  } catch {
    return fallback
  }
}

// 保存默认工作流配置到 localStorage（仅前端状态）。
export function saveWorkflowConfig(config: WorkflowConfig): void {
  try {
    localStorage.setItem(WORKFLOW_CONFIG_STORAGE_KEY, JSON.stringify(config))
  } catch {
    // 忽略存储异常（例如隐私模式禁用 localStorage）
  }
}
