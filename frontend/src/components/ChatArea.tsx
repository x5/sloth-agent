import { useEffect, useRef, useState, useMemo, useCallback } from "react";

import * as api from "../api/client";
import { streamChatMessage } from "../api/client";
import type { Message } from "../api/client";
import { useAgentStore } from "../stores/agentStore";
import { useBrainstormStore } from "../stores/brainstormStore";
import { useInspirationStore } from "../stores/inspirationStore";
import { useUIStore } from "../stores/uiStore";
import { formatTime as formatMessageTime } from "../utils/time";

import BrainstormStreamBubble from "./BrainstormStreamBubble";
import { getRootId, threadColor } from "../utils/threadColor";

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
  }, [activeId, fetchTeam]);

  // Brainstorm store
  const brainstormSessions = useBrainstormStore((s) => s.sessions);
  const brainstormFetchAll = useBrainstormStore((s) => s.fetchAll);
  const brainstormMode = useBrainstormStore((s) => s.brainstormMode);
  const brainstormActiveId = useBrainstormStore((s) => s.activeId);
  const brainstormStart = useBrainstormStore((s) => s.startBrainstorm);
  const brainstormStop = useBrainstormStore((s) => s.stopBrainstorm);
  const brainstormDiscuss = useBrainstormStore((s) => s.startDiscussion);
  const brainstormStopDiscuss = useBrainstormStore((s) => s.stopDiscussion);
  const brainstormConnect = useBrainstormStore((s) => s.connectSession);
  const brainstormDisconnect = useBrainstormStore((s) => s.disconnectSession);
  const brainstormInject = useBrainstormStore((s) => s.injectMessage);
  const brainstormSetReplyingTo = useBrainstormStore((s) => s.setReplyingTo);
  const discussionActive = useBrainstormStore((s) => s.discussionActive);
  const discussionConnected = useBrainstormStore((s) => s.discussionConnected);
  const activeAgentId = useBrainstormStore((s) => s.activeAgentId);
  const activeAgentName = useBrainstormStore((s) => s.activeAgentName);
  const activeAgentNumber = useBrainstormStore((s) => s.activeAgentNumber);
  const discussionMessages = useBrainstormStore((s) => s.discussionMessages);
  const streamingContent = useBrainstormStore((s) => s.streamingContent);
  const replyingToId = useBrainstormStore((s) => s.replyingToId);
  const replyingToContent = useBrainstormStore((s) => s.replyingToContent);

  useEffect(() => {
    if (activeId) {
      brainstormFetchAll(activeId);
    }
  }, [activeId, brainstormFetchAll]);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Chat streaming state
  const [chatStreamText, setChatStreamText] = useState("");
  const chatAbortRef = useRef<AbortController | null>(null);

  // Message queue — ref to avoid closure stale issues; stores individual messages (not merged)
  const queueRef = useRef<string[]>([]);
  const [queueLen, setQueueLen] = useState(0);

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
    prevDiscussionCountRef.current = 0;
  }, [loadMessages]);

  // Persistent brainstorm connection lifecycle
  useEffect(() => {
    if (!brainstormMode || !brainstormActiveId) return;
    let cancelled = false;
    brainstormConnect(brainstormActiveId).catch((e) => {
      if (!cancelled) console.warn("Brainstorm connect failed:", e);
    });
    return () => {
      cancelled = true;
      brainstormDisconnect();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [brainstormMode, brainstormActiveId]);

  useEffect(() => {
    // Auto-scroll only if user is near the bottom
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      if (scrollHeight - scrollTop - clientHeight < 150) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    }
  }, [messages]);

  // Auto-scroll when streaming token content changes (brainstorm or chat)
  useEffect(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 300) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [streamingContent, chatStreamText]);  const prevDiscussionCountRef = useRef(0);
  useEffect(() => {
    const prev = prevDiscussionCountRef.current;
    const curr = discussionMessages.length;
    if (curr > prev) {
      const newMsgs = discussionMessages.slice(prev);
      setMessages((m) => [...m, ...newMsgs]);
    }
    prevDiscussionCountRef.current = curr;
  }, [discussionMessages]);

  // Push dividers when active brainstorm session changes
  const prevSessionRef = useRef<string | null>(null);
  const prevModeRef = useRef(false);
  useEffect(() => {
    const prev = prevSessionRef.current;
    const wasMode = prevModeRef.current;
    if (prev === brainstormActiveId && wasMode === brainstormMode) return;
    prevSessionRef.current = brainstormActiveId;
    prevModeRef.current = brainstormMode;

    // Brainstorm turned OFF — push "Ended" divider for previous session
    if (wasMode && !brainstormMode && prev) {
      const oldNum = sessionNum(brainstormSessions, prev);
      setDividers((d) => [...d, {
        id: `div-end-${Date.now()}`,
        type: "divider",
        variant: "end",
        label: `Brainstorm #${oldNum} Ended`,
        ts: new Date().toISOString(),
      }]);
      return;
    }

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
        label: `Brainstorm #${oldNum} → Brainstorm #${newNum}`,
        ts: new Date().toISOString(),
      });
    }
    newDividers.push({
      id: `div-start-${Date.now() + 1}`,
      type: "divider",
      variant: "start",
      label: `Brainstorm #${newNum} Started`,
      ts: new Date().toISOString(),
    });
    setDividers((d) => [...d, ...newDividers]);
  }, [brainstormActiveId, brainstormMode, brainstormSessions]);

  const handleToggleBrainstorm = useCallback(async () => {
    if (!activeId) return;
    if (!brainstormMode) {
      await brainstormStart(activeId);
    } else {
      brainstormStop();
    }
  }, [activeId, brainstormMode, brainstormStart, brainstormStop]);

  // ---- Message queue: batch all queued messages into one request ----

  const makeHumanMsg = useCallback((content: string): Message => ({
    id: "temp-" + Date.now(),
    inspiration_id: activeId || "",
    agent_id: null,
    role: "human",
    content,
    created_at: new Date().toISOString(),
    agent_name: null,
    agent_number: null,
    agent_model: null,
    mode: brainstormMode ? "brainstorm" : "chat",
    brainstorm_session_id: brainstormMode ? brainstormActiveId : null,
    parent_message_id: null,
    round: 1,
    intent: null,
    truncated: false,
  }), [activeId, brainstormMode, brainstormActiveId]);

  const makeErrMsg = useCallback((content: string): Message => ({
    id: "err-" + Date.now(),
    inspiration_id: activeId || "",
    agent_id: null,
    role: "agent",
    content,
    created_at: new Date().toISOString(),
    agent_name: null,
    agent_number: null,
    agent_model: null,
    mode: brainstormMode ? "brainstorm" : "chat",
    brainstorm_session_id: brainstormMode ? brainstormActiveId : null,
    parent_message_id: null,
    round: 1,
    intent: null,
    truncated: false,
  }), [activeId, brainstormMode, brainstormActiveId]);

  // ---- Helpers: abort any in-flight brainstorm and wait until idle ----

  const waitForDiscussionIdle = useCallback((): Promise<void> => {
    return new Promise((resolve) => {
      if (!useBrainstormStore.getState().discussionActive) { resolve(); return; }
      useBrainstormStore.getState().stopDiscussion();
      const unsub = useBrainstormStore.subscribe((s) => {
        if (!s.discussionActive) { unsub(); resolve(); }
      });
      // Safety fallback: 2s max wait
      setTimeout(() => { unsub(); resolve(); }, 2000);
    });
  }, []);

  // ---- Shared send logic for a single message ----

  const sendOne = useCallback(async (content: string) => {
    if (!activeId) return;

    if (brainstormMode && brainstormActiveId) {
      if (discussionConnected) {
        // Persistent mode: inject into running engine — no waiting, no aborting
        const replyToId = useBrainstormStore.getState().replyingToId;
        useBrainstormStore.getState().setReplyingTo(null, null);
        setSending(true);
        try {
          await brainstormInject(brainstormActiveId, content, replyToId || undefined);
        } catch (e) {
          setMessages((prev) => [...prev, makeErrMsg("Inject error: " + String(e))]);
        } finally {
          setSending(false);
        }
      } else {
        // Legacy fallback (no persistent connection)
        if (discussionActive) {
          await waitForDiscussionIdle();
        }
        prevDiscussionCountRef.current = discussionMessages.length;
        setMessages((prev) => [...prev, makeHumanMsg(content)]);
        setSending(true);
        try {
          await brainstormDiscuss(brainstormActiveId, content);
          useBrainstormStore.setState({ discussionMessages: [] });
          prevDiscussionCountRef.current = 0;
        } catch (e) {
          setMessages((prev) => [...prev, makeErrMsg("Discussion error: " + String(e))]);
        } finally {
          setSending(false);
        }
      }
    } else {
      // Chat mode: SSE streaming
      setMessages((prev) => [...prev, makeHumanMsg(content)]);
      setChatStreamText("");
      setSending(true);
      const abort = new AbortController();
      chatAbortRef.current = abort;
      let accumulated = "";
      try {
        for await (const chunk of streamChatMessage(activeId, content, { mode: "chat" }, abort.signal)) {
          if (chunk.done) break;
          if (chunk.error) throw new Error(chunk.error);
          if (chunk.token) {
            accumulated += chunk.token;
            setChatStreamText(accumulated);
          }
        }
        // Commit final message to messages array
        if (accumulated) {
          setMessages((prev) => [
            ...prev,
            {
              id: "stream-" + Date.now(),
              inspiration_id: activeId,
              agent_id: null,
              role: "agent",
              content: accumulated,
              created_at: new Date().toISOString(),
              agent_name: null,
              agent_number: null,
              agent_model: null,
              mode: "chat",
              brainstorm_session_id: null,
              parent_message_id: null,
              round: 1,
              intent: null,
              truncated: false,
            },
          ]);
        }
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setMessages((prev) => [...prev, makeErrMsg("Error: " + String(e))]);
        }
      } finally {
        chatAbortRef.current = null;
        setChatStreamText("");
        setSending(false);
      }
    }
  }, [activeId, brainstormMode, brainstormActiveId, discussionActive, discussionConnected,
      discussionMessages.length, brainstormDiscuss, brainstormInject, waitForDiscussionIdle,
      makeHumanMsg, makeErrMsg]);

  // ---- Process queue: drain one message at a time ----

  const processQueue = useCallback(async () => {
    if (queueRef.current.length === 0) return;
    const next = queueRef.current.shift()!;
    setQueueLen(queueRef.current.length);
    await sendOne(next);
    await processQueue(); // await to propagate errors and ensure serial drain
  }, [sendOne]);

  const handleSend = async () => {
    const content = input.trim();
    if (!content || !activeId) return;
    setInput("");

    // System busy → enqueue individually (no merging)
    if (sending) {
      queueRef.current.push(content);
      setQueueLen(queueRef.current.length);
      return;
    }

    await sendOne(content);
    await processQueue();
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
            <DisplayItems messages={messages} dividers={dividers} formatMessageTime={formatMessageTime} agentColorMap={agentColorMap} brainstormMode={brainstormMode} onReply={(id, preview) => brainstormSetReplyingTo(id, preview)} />
            {/* Brainstorm: show real-time token stream for active agent */}
            {discussionActive && activeAgentId && (() => {
              const agentColor = activeAgentNumber ? (agentColorMap[activeAgentNumber] ?? "#94A3B8") : "#94A3B8";
              return (
                <BrainstormStreamBubble
                  agentName={activeAgentName || "Agent"}
                  agentNumber={activeAgentNumber}
                  agentColor={agentColor}
                  streamingContent={streamingContent}
                />
              );
            })()}
            {/* Chat mode: show streaming bubble while LLM is typing */}
            {sending && !brainstormMode && chatStreamText && (
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
                </div>
                <div className="chat-message__bubble">
                  <div className="chat-message__content">
                    {chatStreamText}
                    <span className="brainstorm-cursor">▌</span>
                  </div>
                </div>
              </div>
            )}
            {sending && !brainstormMode && !chatStreamText && <ThinkingBubble />}
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
        {brainstormMode && replyingToId && replyingToContent && (
          <div className="chatarea__reply-bar">
            <span className="chatarea__reply-bar__arrow">↩</span>
            <span className="chatarea__reply-bar__text">回复 {replyingToContent}</span>
            <button className="chatarea__reply-bar__close" onClick={() => brainstormSetReplyingTo(null, null)}>✕</button>
          </div>
        )}
        {queueLen > 0 && (
          <div className="chatarea__queue-badge">
            {queueLen} message{queueLen > 1 ? "s" : ""} queued
          </div>
        )}
        <div className={`chatarea__input-box${brainstormMode ? " chatarea__input-box--brainstorm" : ""}`}>
          <textarea
            className="chatarea__input-field chatarea__input-field--active"
            placeholder={
              activeInspiration
                ? brainstormMode && discussionActive
                  ? "Type to interrupt the discussion..."
                  : "Type your message..."
                : "Select an inspiration to start..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!activeInspiration}
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
                disabled={!activeInspiration}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              </button>
            </div>
            {brainstormMode && (discussionActive || discussionConnected) ? (
              <button
                className="chatarea__stop-btn"
                onClick={() => discussionConnected ? brainstormDisconnect() : brainstormStopDiscuss()}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="4" y="4" width="16" height="16" rx="2" />
                </svg>
                <span>Stop</span>
              </button>
            ) : (
              <button
                className="chatarea__send-btn"
                disabled={!activeInspiration || !input.trim()}
                onClick={handleSend}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </button>
            )}
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
  brainstormMode,
  onReply,
}: {
  messages: Message[];
  dividers: DividerItem[];
  formatMessageTime: (iso: string) => string;
  agentColorMap: Record<number, string>;
  brainstormMode: boolean;
  onReply: (id: string, preview: string) => void;
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

        // Thread color line: only in brainstorm mode for reply messages
        const threadLine = brainstormMode && m.parent_message_id
          ? threadColor(getRootId(m.parent_message_id, messages))
          : null;

        // Reply preview: first 30 chars of content (or agent name prefix)
        const replyPreview = (m.agent_name ? `${m.agent_name} · ` : "") + `"${m.content.slice(0, 30)}"`;

        return (
          <div
            key={m.id}
            className={`chat-message${isHuman ? " chat-message--human" : " chat-message--agent"}${brainstormMode ? " chat-message--brainstorm" : ""}`}
            style={threadLine ? { borderLeft: `3px solid ${threadLine}`, paddingLeft: "6px" } : undefined}
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
                  {brainstormMode && (
                    <button
                      className="chat-message__reply-btn"
                      onClick={() => onReply(m.id, replyPreview)}
                      title="Reply"
                    >
                      ↩
                    </button>
                  )}
                </div>
              )}
              {isHuman && (
                <div className="chat-message__agent-info">
                  <span className="chat-message__role">You</span>
                  <span className="chat-message__time">{formatMessageTime(m.created_at)}</span>
                  {brainstormMode && (
                    <button
                      className="chat-message__reply-btn"
                      onClick={() => onReply(m.id, replyPreview)}
                      title="Reply"
                    >
                      ↩
                    </button>
                  )}
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

function ThinkingBubble({ agentName, agentNumber }: { agentName?: string; agentNumber?: number } = {}) {
  const [message] = useState(() => pick(THINKING_MESSAGES));
  const [color] = useState(() => pick(THINKING_COLORS));

  return (
    <div className="chat-message chat-message--agent">
      {agentName && (
        <div className="chat-message__avatar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="8" width="18" height="12" rx="3" />
            <circle cx="9" cy="14" r="2" />
            <circle cx="15" cy="14" r="2" />
            <line x1="9" y1="6" x2="9" y2="4" />
            <line x1="15" y1="6" x2="15" y2="4" />
            <line x1="12" y1="6" x2="12" y2="3" />
          </svg>
          <span className="chat-message__avatar-num">{agentNumber ?? "?"}</span>
        </div>
      )}
      <div className="chat-message__bubble">
        {agentName && (
          <div className="chat-message__agent-info">
            <span className="chat-message__agent-name">{agentName}</span>
          </div>
        )}
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
