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
export const CURRENT_OCR_PROVIDER = "MinerU"
export const CURRENT_AI_ENGINE = "DeepSeek"
