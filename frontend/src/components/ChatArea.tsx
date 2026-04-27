import { useEffect, useRef, useState } from "react";
import { useInspirationStore } from "../stores/inspirationStore";
import { useUIStore } from "../stores/uiStore";
import * as api from "../api/client";
import type { Message } from "../api/client";

function formatMessageTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  if (isToday) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return (
    date.toLocaleDateString([], { month: "short", day: "numeric" }) +
    " " +
    date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  );
}

export default function ChatArea() {
  const inspirations = useInspirationStore((s) => s.inspirations);
  const activeId = useInspirationStore((s) => s.activeId);
  const activeInspiration = inspirations.find((i) => i.id === activeId);

  const col4Content = useUIStore((s) => s.col4Content);
  const openCol4 = useUIStore((s) => s.openCol4);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeId) {
      api.getMessages(activeId).then(setMessages).catch(() => setMessages([]));
    } else {
      setMessages([]);
    }
    setInput("");
  }, [activeId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    const content = input.trim();
    if (!content || !activeId || sending) return;

    setInput("");
    setSending(true);

    // Optimistic human message
    const tempHuman: Message = {
      id: "temp-" + Date.now(),
      inspiration_id: activeId,
      agent_id: null,
      role: "human",
      content,
      created_at: new Date().toISOString(),
      agent_name: null,
      agent_number: null,
      agent_model: null,
    };
    setMessages((prev) => [...prev, tempHuman]);

    try {
      const reply = await api.sendChatMessage(activeId, content);
      setMessages((prev) => [...prev, reply]);
    } catch (e) {
      const errMsg: Message = {
        id: "err-" + Date.now(),
        inspiration_id: activeId,
        agent_id: null,
        role: "agent",
        content: "Error: " + String(e),
        created_at: new Date().toISOString(),
        agent_name: null,
        agent_number: null,
        agent_model: null,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chatarea">
      {/* TopAppBar */}
      <div className="chatarea__topbar">
        <div className="chatarea__topbar-left">
          {activeInspiration ? (
            <>
              <h2 className="chatarea__project-name">{activeInspiration.name}</h2>
              <span className="chatarea__status">
                <span className="chatarea__status-dot" />
                {activeInspiration.agent_count === 1 ? "1 Agent active" : `${activeInspiration.agent_count} Agents active`}
              </span>
            </>
          ) : (
            <h2 className="chatarea__project-name chatarea__project-name--dimmed">
              Sloth Agent
            </h2>
          )}
        </div>
        <div className="chatarea__topbar-actions">
          <button className={`chatarea__icon-btn${col4Content === "team" ? " chatarea__icon-btn--active" : ""}`} title="Team" onClick={() => openCol4("team")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="8" r="4" />
              <path d="M1 20v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2" />
              <circle cx="18" cy="8" r="3" />
              <path d="M22 20v-2a3 3 0 0 0-2-2.8" />
            </svg>
          </button>
          <button className={`chatarea__icon-btn${col4Content === "status" ? " chatarea__icon-btn--active" : ""}`} title="Status" onClick={() => openCol4("status")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </button>
          <button className="chatarea__icon-btn" title="More Options">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chatarea__canvas" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chatarea__empty">
            <div className="chatarea__empty-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c7c7c7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
              </svg>
            </div>
            <p className="chatarea__empty-text">
              {activeInspiration
                ? `Start chatting in "${activeInspiration.name}"`
                : "Select an inspiration to start chatting"}
            </p>
          </div>
        ) : (
          <div className="chatarea__messages">
            {messages.map((m) => {
              const isHuman = m.role === "human";
              return (
                <div
                  key={m.id}
                  className={`chat-message${isHuman ? " chat-message--human" : " chat-message--agent"}`}
                >
                  {!isHuman && (
                    <div className="chat-message__avatar">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="8" width="18" height="12" rx="3" />
                        <circle cx="9" cy="14" r="2" />
                        <circle cx="15" cy="14" r="2" />
                        <line x1="9" y1="6" x2="9" y2="4" />
                        <line x1="15" y1="6" x2="15" y2="4" />
                        <line x1="12" y1="6" x2="12" y2="3" />
                      </svg>
                      <span className="chat-message__avatar-num">{m.agent_number ?? "?"}</span>
                    </div>
                  )}
                  <div className="chat-message__bubble">
                    {!isHuman && (
                      <div className="chat-message__agent-info">
                        <span className="chat-message__agent-name">{m.agent_name || "Agent"}</span>
                        {m.agent_model && (
                          <span className="chat-message__agent-model">{m.agent_model}</span>
                        )}
                        <span className="chat-message__time">{formatMessageTime(m.created_at)}</span>
                      </div>
                    )}
                    {isHuman && (
                      <div className="chat-message__agent-info">
                        <span className="chat-message__role">You</span>
                        <span className="chat-message__time">{formatMessageTime(m.created_at)}</span>
                      </div>
                    )}
                    <div className="chat-message__content">{m.content}</div>
                  </div>
                </div>
              );
            })}
            {sending && (
              <div className="chat-message chat-message--agent">
                <div className="chat-message__bubble">
                  <div className="chat-message__content chat-message__content--loading">
                    Thinking...
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="chatarea__input">
        <div className="chatarea__input-box">
          <textarea
            className="chatarea__input-field chatarea__input-field--active"
            placeholder={
              activeInspiration
                ? "Type your message..."
                : "Select an inspiration to start..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!activeInspiration || sending}
            rows={3}
          />
          <div className="chatarea__input-actions">
            <div className="chatarea__input-tools">
              <button className="chatarea__tool-btn" title="Attach File" disabled>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <button className="chatarea__tool-btn" title="Mention Agent" disabled>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </button>
            </div>
            <button
              className="chatarea__send-btn"
              disabled={!activeInspiration || !input.trim() || sending}
              onClick={handleSend}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
