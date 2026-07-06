export function resolveSessionToken(tokenFromEnv: string | undefined): string {
  const token = tokenFromEnv?.trim()
  if (!token) {
    throw new Error(
      "Missing VITE_GREAT_OCR_TOKEN. Please start GreatOCR using start.bat.",
    )
  }
  return token
}
