import { useState } from "react";

import type { ToolCallEntry } from "../api/client";

interface ToolCallItemProps {
  call: ToolCallEntry;
  defaultOpen: boolean;
}

function ToolCallItem({ call, defaultOpen }: ToolCallItemProps) {
  const [open, setOpen] = useState(defaultOpen);
  const pending = call.success === undefined;
  const failed = call.success === false;

  return (
    <div
      className={`tool-call-item ${pending ? "tool-call-item--pending" : ""} ${failed ? "tool-call-item--failed" : ""}`}
    >
      <button
        type="button"
        className="tool-call-item__header"
        onClick={() => setOpen(!open)}
      >
        <span className="tool-call-item__icon">
          {pending ? "⏳" : failed ? "❌" : "✅"}
        </span>
        <span className="tool-call-item__name">
          {"🔧"} {call.tool_name}
        </span>
        <span className="tool-call-item__chevron">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <div className="tool-call-item__body">
          <div className="tool-call-item__section">
            <span className="tool-call-item__label">Arguments</span>
            <pre className="tool-call-item__json">
              {JSON.stringify(call.arguments, null, 2)}
            </pre>
          </div>
          {call.output !== undefined && (
            <div className="tool-call-item__section">
              <span className="tool-call-item__label">Result</span>
              <pre className="tool-call-item__result">
                {call.output
                  ? call.output.slice(0, 200) + (call.output.length > 200 ? "…" : "")
                  : "(empty)"}
              </pre>
            </div>
          )}
          {call.error_code && (
            <div className="tool-call-item__error">Error: {call.error_code}</div>
          )}
        </div>
      )}
    </div>
  );
}

interface ToolCallBlockProps {
  toolCalls: ToolCallEntry[];
}

export default function ToolCallBlock({ toolCalls }: ToolCallBlockProps) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="tool-call-block">
      {toolCalls.map((call, i) => (
        <ToolCallItem
          key={`${call.tool_name}-${i}`}
          call={call}
          defaultOpen={i === toolCalls.length - 1}
        />
      ))}
    </div>
  );
}
