import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it } from "vitest"

import { App } from "./App"

describe("GreatOCR application shell", () => {
  it("renders the primary navigation", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText("任务中心")).toBeInTheDocument()
    expect(screen.getByText("新建任务")).toBeInTheDocument()
    expect(screen.getByText("设置")).toBeInTheDocument()
  })
})
