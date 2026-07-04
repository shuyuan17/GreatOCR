import { describe, expect, it } from "vitest"

import { validatePageRange } from "./pageRanges"

describe("validatePageRange", () => {
  it("accepts an empty value for all pages", () => {
    expect(validatePageRange("")).toBe("")
    expect(validatePageRange("   ")).toBe("")
  })

  it("accepts supported page range formats", () => {
    expect(validatePageRange("1")).toBe("")
    expect(validatePageRange("1-3")).toBe("")
    expect(validatePageRange("1,3,5")).toBe("")
    expect(validatePageRange("1-3,5,7-9")).toBe("")
  })

  it("rejects invalid page range formats", () => {
    expect(validatePageRange("0")).toContain("页码范围")
    expect(validatePageRange("3-1")).toContain("页码范围")
    expect(validatePageRange("1,,3")).toContain("页码范围")
    expect(validatePageRange("a-b")).toContain("页码范围")
  })
})
