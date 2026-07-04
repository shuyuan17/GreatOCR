/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GREAT_OCR_TOKEN?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

interface Window {
  __GREAT_OCR_TOKEN__: string
}
