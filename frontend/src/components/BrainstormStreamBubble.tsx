import type { ToolCallEntry } from "../api/client";

import ToolCallBlock from "./ToolCallBlock";

interface ParentMsgPreview {
  agent_name: string | null;
  content: string;
}

interface Props {
  agentName: string;
  agentNumber?: number | null;
  agentColor?: string;
  streamingContent?: string;
  parentMsg?: ParentMsgPreview | null;
  quoteAccent?: string | null;
  toolCalls?: ToolCallEntry[];
}

export default function BrainstormStreamBubble({ agentName, agentNumber, agentColor, streamingContent, parentMsg, quoteAccent, toolCalls }: Props) {
  const color = agentColor || "#94A3B8";
  const hasContent = streamingContent && streamingContent.length > 0;

  return (
    <div className="chat-message chat-message--agent">
      <div className="chat-message__avatar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="8" width="18" height="12" rx="3" />
          <circle cx="9" cy="14" r="2" />
          <circle cx="15" cy="14" r="2" />
          <line x1="9" y1="6" x2="9" y2="4" />
          <line x1="15" y1="6" x2="15" y2="4" />
          <line x1="12" y1="6" x2="12" y2="3" />
        </svg>
        <span
          className="chat-message__avatar-num"
          style={agentNumber ? { color, borderColor: `${color}44`, background: `${color}12` } : undefined}
        >
          {agentNumber ?? "?"}
        </span>
      </div>
      <div className="chat-message__bubble">
        <div className="chat-message__agent-info">
          <span className="chat-message__agent-name">{agentName}</span>
          <span className="chat-message__time" style={{ color }}>typing…</span>
        </div>
        {parentMsg && (
          <div className="chat-message__quote" style={quoteAccent ? { borderLeftColor: quoteAccent } : undefined}>
            <span className="chat-message__quote-author">{parentMsg.agent_name || "You"}</span>
            <span className="chat-message__quote-text">
              {parentMsg.content.slice(0, 80)}{parentMsg.content.length > 80 ? "…" : ""}
            </span>
          </div>
        )}
        <div className="chat-message__content">
          {hasContent ? (
            <span>
              {streamingContent}
              <span className="brainstorm-cursor" style={{ color }}>▌</span>
            </span>
          ) : (
            <span className="chat-message__content--thinking">
              <span className="thinking-dots">
                <span className="thinking-dot" style={{ color }}>.</span>
                <span className="thinking-dot" style={{ color }}>.</span>
                <span className="thinking-dot" style={{ color }}>.</span>
              </span>
            </span>
          )}
        </div>
        {toolCalls && toolCalls.length > 0 && (
          <ToolCallBlock toolCalls={toolCalls} />
        )}
      </div>
    </div>
  );
}
