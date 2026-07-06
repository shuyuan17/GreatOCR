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

// AI Processing Mode。
export const AI_PROCESSING_MODES: Option<AiModeValue>[] = [
  {
    value: "ocr",
    label: "OCR Only",
    description: "仅执行 OCR，生成 result.docx",
  },
  {
    value: "translation",
    label: "Translation",
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

// 当前 OCR Provider / AI Engine 展示名称（UI 展示用，本任务不做真实配置校验）。
// 注意：新版 Settings / 新建任务页改用下方的 DEFAULT_*_PROVIDER 与 AI_PROVIDER_CATALOG。
export const CURRENT_OCR_PROVIDER = "MinerU"
export const CURRENT_AI_ENGINE = "DeepSeek"

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

// AI Provider 目录：Settings 页「AI Provider Library」的展示数据来源。
// - 真实可配置的 Provider（MinerU / DeepSeek）标记为 active。
// - 计划中的 Provider 标记为 comingSoon（disabled 卡片，不可配置）。
// - fake-default 仅用于离线测试，不进入此目录，正式 UI 不展示。
export interface AiProviderCatalogEntry {
  profileId: string
  displayName: string
  capabilities: ProviderCapability[]
  sensitiveAllowed: boolean
  comingSoon?: boolean
}

export const AI_PROVIDER_CATALOG: AiProviderCatalogEntry[] = [
  {
    profileId: "mineru-default",
    displayName: "MinerU",
    capabilities: ["OCR"],
    sensitiveAllowed: false,
  },
  {
    profileId: "deepseek-default",
    displayName: "DeepSeek",
    capabilities: ["Translation", "Text Processing"],
    sensitiveAllowed: false,
  },
  // ---- Coming Soon（disabled 卡片，V2.4 起可用）----
  {
    profileId: "openai",
    displayName: "OpenAI",
    capabilities: ["Translation", "Summary", "Formatting"],
    sensitiveAllowed: false,
    comingSoon: true,
  },
  {
    profileId: "azure-doc-intel",
    displayName: "Azure Document Intelligence",
    capabilities: ["OCR"],
    sensitiveAllowed: false,
    comingSoon: true,
  },
  {
    profileId: "local-model",
    displayName: "Local Model",
    capabilities: ["OCR", "Translation"],
    sensitiveAllowed: true,
    comingSoon: true,
  },
]

// 默认工作流配置（UI 展示用，本任务不做真实保存）。
export const DEFAULT_OCR_PROVIDER = "MinerU"
export const DEFAULT_TRANSLATION_PROVIDER = "DeepSeek"
