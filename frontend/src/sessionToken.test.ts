import { describe, expect, it } from "vitest"

import { resolveSessionToken } from "./sessionToken"

describe("resolveSessionToken", () => {
  it("returns the provided startup token", () => {
    expect(resolveSessionToken(" release-token ")).toBe("release-token")
  })

  it("fails clearly when startup token is missing", () => {
    expect(() => resolveSessionToken("")).toThrow(/VITE_GREAT_OCR_TOKEN/)
    expect(() => resolveSessionToken(undefined)).toThrow(/start\.bat/i)
  })
})
