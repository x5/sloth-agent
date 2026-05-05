import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { ToolCallEntry } from "../api/client";

import ToolCallBlock from "./ToolCallBlock";

const pendingCall: ToolCallEntry = {
  tool_name: "read",
  arguments: { path: "test.txt" },
};

const successCall: ToolCallEntry = {
  tool_name: "read",
  arguments: { path: "test.txt" },
  success: true,
  output: "file content here",
};

const failedCall: ToolCallEntry = {
  tool_name: "read",
  arguments: { path: "missing.txt" },
  success: false,
  output: "File not found",
  error_code: "FILE_NOT_FOUND",
};

const longOutputCall: ToolCallEntry = {
  tool_name: "grep_repo",
  arguments: { pattern: "TODO" },
  success: true,
  output: "x".repeat(300),
};

describe("ToolCallBlock", () => {
  it("renders empty list as null", () => {
    const { container } = render(<ToolCallBlock toolCalls={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders pending call", () => {
    render(<ToolCallBlock toolCalls={[pendingCall]} />);
    expect(screen.getByText(/read/)).toBeDefined();
  });

  it("renders success call with checkmark", () => {
    render(<ToolCallBlock toolCalls={[successCall]} />);
    expect(screen.getByText(/file content here/)).toBeDefined();
  });

  it("renders failed call with error", () => {
    render(<ToolCallBlock toolCalls={[failedCall]} />);
    expect(screen.getByText(/FILE_NOT_FOUND/)).toBeDefined();
  });

  it("click header toggles expand", async () => {
    const user = userEvent.setup();
    render(<ToolCallBlock toolCalls={[successCall]} />);

    // Initially expanded (defaultOpen=true for last item)
    expect(screen.getByText("Arguments")).toBeDefined();

    await user.click(screen.getByText(/read/));
    // Arguments should now be hidden
    expect(screen.queryByText("Arguments")).toBeNull();
  });

  it("truncates long result output", () => {
    render(<ToolCallBlock toolCalls={[longOutputCall]} />);
    const resultText = screen.getByText(/x+/);
    expect(resultText.textContent?.length).toBeLessThan(250);
  });
});
