const PAGE_RANGE_ERROR = "页码范围格式不正确，请使用 1、1-3、1,3,5 或 1-3,5,7-9"

export function isPdfFile(file: File | null): boolean {
  if (!file) return false
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
}

export function validatePageRange(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) return ""

  const tokens = trimmed.split(",")
  if (tokens.some((token) => token.trim() === "")) {
    return PAGE_RANGE_ERROR
  }

  for (const token of tokens) {
    const normalized = token.trim()
    if (/^\d+$/.test(normalized)) {
      if (Number(normalized) < 1) {
        return PAGE_RANGE_ERROR
      }
      continue
    }

    const match = normalized.match(/^(\d+)-(\d+)$/)
    if (!match) {
      return PAGE_RANGE_ERROR
    }

    const start = Number(match[1])
    const end = Number(match[2])
    if (start < 1 || end < 1 || start > end) {
      return PAGE_RANGE_ERROR
    }
  }

  return ""
}
