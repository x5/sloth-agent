import { useEffect, useRef, useState, useMemo, useCallback } from "react";
import { useInspirationStore } from "../stores/inspirationStore";
import { useUIStore } from "../stores/uiStore";
import { useAgentStore } from "../stores/agentStore";
import { useBrainstormStore } from "../stores/brainstormStore";
import * as api from "../api/client";
import type { Message } from "../api/client";
import { formatTime as formatMessageTime } from "../utils/time";

interface DividerItem {
  id: string;
  type: "divider";
  variant: "start" | "end" | "transition";
  label: string;
  ts: string;
}

function BrainstormDivider({ label, variant }: { label: string; variant: "start" | "end" | "transition" }) {
  return (
    <div className={`brainstorm-divider brainstorm-divider--${variant}`}>
      <span className="brainstorm-divider__line" />
      <span className="brainstorm-divider__label">{label}</span>
      <span className="brainstorm-divider__line" />
    </div>
  );
}

/** Sessions array is newest-first. Oldest = #1, newest = #N. */
function sessionNum(sessions: { id: string }[], sessionId: string): number {
  const idx = sessions.findIndex((s) => s.id === sessionId);
  if (idx < 0) return sessions.length + 1;
  return sessions.length - idx;
}

const ROLE_COLOR: Record<string, string> = {
  lead: "#8B5CF6",
  fortune: "#06B6D4",
};

export default function ChatArea() {
  const inspirations = useInspirationStore((s) => s.inspirations);
  const activeId = useInspirationStore((s) => s.activeId);
  const activeInspiration = inspirations.find((i) => i.id === activeId);

  const col4Content = useUIStore((s) => s.col4Content);
  const openCol4 = useUIStore((s) => s.openCol4);

  const teamMembers = useAgentStore((s) => s.teamMembers);
  const fetchTeam = useAgentStore((s) => s.fetchTeam);
  const workingCount = teamMembers.filter((m) => m.status === "working").length;

  const agentColorMap = useMemo(() => {
    const map: Record<number, string> = {};
    teamMembers.forEach((m, i) => {
      map[i + 1] = ROLE_COLOR[m.role] ?? "#94A3B8";
    });
    return map;
  }, [teamMembers]);

  useEffect(() => {
    if (activeId) {
      fetchTeam(activeId);
    }
  }, [activeId]);

  // Brainstorm store
  const brainstormSessions = useBrainstormStore((s) => s.sessions);
  const brainstormFetchAll = useBrainstormStore((s) => s.fetchAll);
  const brainstormMode = useBrainstormStore((s) => s.brainstormMode);
  const brainstormActiveId = useBrainstormStore((s) => s.activeId);
  const brainstormStart = useBrainstormStore((s) => s.startBrainstorm);
  const brainstormStop = useBrainstormStore((s) => s.stopBrainstorm);

  useEffect(() => {
    if (activeId) {
      brainstormFetchAll(activeId);
    }
  }, [activeId]);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Brainstorm dividers (local state)
  const [dividers, setDividers] = useState<DividerItem[]>([]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 150);
  };

  const loadMessages = useCallback(async () => {
    if (!activeId) { setMessages([]); return; }
    try {
      const msgs = await api.getMessages(
        activeId,
        undefined,
        undefined,
        brainstormMode ? brainstormActiveId : null,
      );
      setMessages(msgs);
    } catch {
      setMessages([]);
    }
  }, [activeId, brainstormMode, brainstormActiveId]);

  useEffect(() => {
    loadMessages();
    setInput("");
  }, [loadMessages]);

  useEffect(() => {
    // Auto-scroll only if user is near the bottom
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      if (scrollHeight - scrollTop - clientHeight < 150) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }
  }, [messages]);

  // Push dividers when active brainstorm session changes
  const prevSessionRef = useRef<string | null>(null);
  useEffect(() => {
    const prev = prevSessionRef.current;
    if (prev === brainstormActiveId) return;
    prevSessionRef.current = brainstormActiveId;

    if (!brainstormMode) return;
    if (!brainstormActiveId) return;

    const newNum = sessionNum(brainstormSessions, brainstormActiveId);
    const newDividers: DividerItem[] = [];
    if (prev) {
      const oldNum = sessionNum(brainstormSessions, prev);
      newDividers.push({
        id: `div-switch-${Date.now()}`,
        type: "divider",
        variant: "transition",
        label: `Session #${oldNum} → Session #${newNum}`,
        ts: new Date().toISOString(),
      });
    }
    newDividers.push({
      id: `div-start-${Date.now() + 1}`,
      type: "divider",
      variant: "start",
      label: `Session #${newNum} Started`,
      ts: new Date().toISOString(),
    });
    setDividers((d) => [...d, ...newDividers]);
  }, [brainstormActiveId, brainstormMode, brainstormSessions]);

  const handleToggleBrainstorm = useCallback(async () => {
    if (!activeId || sending) return;
    if (!brainstormMode) {
      await brainstormStart(activeId);
    } else {
      brainstormStop();
    }
  }, [activeId, sending, brainstormMode, brainstormStart, brainstormStop]);

  const handleSend = async () => {
    const content = input.trim();
    if (!content || !activeId || sending) return;

    setInput("");
    setSending(true);

    const mode = brainstormMode ? "brainstorm" : "chat";
    const sessionId = brainstormMode ? brainstormActiveId : null;

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
      mode,
      brainstorm_session_id: sessionId,
    };
    setMessages((prev) => [...prev, tempHuman]);

    try {
      const reply = await api.sendChatMessage(activeId, content, { mode, brainstormSessionId: sessionId ?? undefined });
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
        mode,
        brainstorm_session_id: sessionId,
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
              <span
                className="chatarea__status"
                data-tooltip-bottom={workingCount > 0
                  ? `${workingCount} AGENT${workingCount > 1 ? "S" : ""} WORKING`
                  : `${teamMembers.length} AGENT${teamMembers.length !== 1 ? "S" : ""} IDLE`}
              >
                <span className={`chatarea__status-dot${workingCount > 0 ? " chatarea__status-dot--working" : " chatarea__status-dot--idle"}`} />
                <span className="chatarea__status-count">{teamMembers.length}</span>
                <svg className="chatarea__status-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="8" width="18" height="12" rx="3" />
                  <circle cx="9" cy="14" r="2" />
                  <circle cx="15" cy="14" r="2" />
                  <line x1="9" y1="6" x2="9" y2="4" />
                  <line x1="15" y1="6" x2="15" y2="4" />
                  <line x1="12" y1="6" x2="12" y2="3" />
                </svg>
              </span>
              {brainstormMode && brainstormActiveId && (() => {
                const sessionIndex = sessionNum(brainstormSessions, brainstormActiveId);
                return (
                  <span className="chatarea__brainstorm-badge" data-tooltip-bottom="Brainstorm Mode Active">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                    </svg>
                    <span>#{sessionIndex}</span>
                  </span>
                );
              })()}
            </>
          ) : (
            <h2 className="chatarea__project-name chatarea__project-name--dimmed">
              Sloth Agent
            </h2>
          )}
        </div>
        <div className="chatarea__topbar-actions">
          <button className={`chatarea__icon-btn${col4Content === "team" ? " chatarea__icon-btn--active" : ""}`} data-tooltip-bottom="Team" onClick={() => openCol4("team")} disabled={!activeInspiration}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="8" r="4" />
              <path d="M1 20v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2" />
              <circle cx="18" cy="8" r="3" />
              <path d="M22 20v-2a3 3 0 0 0-2-2.8" />
            </svg>
          </button>
          <button className={`chatarea__icon-btn${col4Content === "status" ? " chatarea__icon-btn--active" : ""}`} data-tooltip-bottom="Status" onClick={() => openCol4("status")} disabled>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </button>
          <button className="chatarea__icon-btn" data-tooltip-bottom="More Options" disabled>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chatarea__canvas" ref={scrollRef} onScroll={handleScroll}>
        {messages.length === 0 && dividers.length === 0 ? (
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
            <DisplayItems messages={messages} dividers={dividers} formatMessageTime={formatMessageTime} agentColorMap={agentColorMap} />
            {sending && <ThinkingBubble />}
          </div>
        )}
        {showScrollBtn && (
          <button className="chatarea__scroll-btn" onClick={() => {
            if (scrollRef.current) {
              scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
            }
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
            New messages
          </button>
        )}
      </div>

      {/* Input Area */}
      <div className="chatarea__input">
        <div className={`chatarea__input-box${brainstormMode ? " chatarea__input-box--brainstorm" : ""}`}>
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
              <button className="chatarea__tool-btn" data-tooltip="Attach File" disabled>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <button className="chatarea__tool-btn" data-tooltip="Mention Agent" disabled>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </button>
              <button
                className={`chatarea__tool-btn${brainstormMode ? " chatarea__tool-btn--active" : ""}`}
                data-tooltip={brainstormMode ? "End Brainstorm" : "Start Brainstorm"}
                onClick={handleToggleBrainstorm}
                disabled={!activeInspiration || sending}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
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

const THINKING_MESSAGES = [
  "Summoning intelligence",
  "Consulting the oracle",
  "Connecting neurons",
  "Brewing fresh thoughts",
  "Crunching tokens",
  "Channeling the muse",
  "Warming up GPUs",
  "Polishing reasoning",
  "Reading between the lines",
  "Untangling logic",
  "Firing synapses",
  "Consulting the sloth",
  "Loading wit",
  "Assembling context",
  "Sharpening the quill",
  "Distilling wisdom",
  "Aligning stars",
  "Calibrating sarcasm",
  "Mining insights",
  "Weaving narrative",
  "Charging creativity",
  "Decoding intentions",
  "Bending spacetime",
  "Reconciling paradoxes",
  "Buffering brilliance",
  "Invoking the daemon",
  "Priming the oracle",
  "Translating thought",
  "Baking the answer",
  "De-fragmenting memory",
  "Negotiating with tokens",
  "Reticulating splines",
];

const THINKING_COLORS = [
  "#14a0c8", "#6366f1", "#8b5cf6", "#ec4899",
  "#f59e0b", "#22c55e", "#3b82f6", "#ef4444",
  "#06b6d4", "#a855f7", "#d946ef", "#84cc16",
];

type DisplayItem = Message | DividerItem;

function DisplayItems({
  messages,
  dividers,
  formatMessageTime,
  agentColorMap,
}: {
  messages: Message[];
  dividers: DividerItem[];
  formatMessageTime: (iso: string) => string;
  agentColorMap: Record<number, string>;
}) {
  const items = useMemo<DisplayItem[]>(() => {
    const sorted = [...dividers].sort((a, b) => a.ts.localeCompare(b.ts));
    const all: DisplayItem[] = [];
    let di = 0;
    for (const msg of messages) {
      while (di < sorted.length && sorted[di].ts < msg.created_at) {
        all.push(sorted[di++]);
      }
      all.push(msg);
    }
    while (di < sorted.length) {
      all.push(sorted[di++]);
    }
    return all;
  }, [messages, dividers]);

  return (
    <>
      {items.map((item) => {
        if ("type" in item && item.type === "divider") {
          return <BrainstormDivider key={item.id} label={item.label} variant={item.variant} />;
        }
        const m = item as Message;
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
                <span className="chat-message__avatar-num" style={m.agent_number && agentColorMap[m.agent_number] ? { color: agentColorMap[m.agent_number], borderColor: `${agentColorMap[m.agent_number]}44`, background: `${agentColorMap[m.agent_number]}12` } : undefined}>{m.agent_number ?? "?"}</span>
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
    </>
  );
}

function pick<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function ThinkingBubble() {
  const [message] = useState(() => pick(THINKING_MESSAGES));
  const [color] = useState(() => pick(THINKING_COLORS));

  return (
    <div className="chat-message chat-message--agent">
      <div className="chat-message__bubble">
        <div className="chat-message__content chat-message__content--thinking">
          <span className="thinking-text" style={{ color }}>
            {message}
          </span>
          <span className="thinking-dots">
            <span className="thinking-dot" style={{ color }}>.</span>
            <span className="thinking-dot" style={{ color }}>.</span>
            <span className="thinking-dot" style={{ color }}>.</span>
          </span>
        </div>
      </div>
    </div>
  );
}
