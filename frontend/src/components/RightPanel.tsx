import { useEffect, useMemo, useRef, useState } from "react";
import { useUIStore } from "../stores/uiStore";
import { useInspirationStore } from "../stores/inspirationStore";
import { useAgentStore } from "../stores/agentStore";
import { useLLMStore } from "../stores/llmStore";
import { useBrainstormStore } from "../stores/brainstormStore";
import { formatTime } from "../utils/time";

const ROLE_COLOR: Record<string, string> = {
  lead: "#8B5CF6",
  fortune: "#06B6D4",
};

/** Sessions array is newest-first. Oldest = #1, newest = #N. */
function sessionNum(sessions: { id: string }[], sessionId: string): number {
  const idx = sessions.findIndex((s) => s.id === sessionId);
  if (idx < 0) return sessions.length + 1;
  return sessions.length - idx;
}

export default function RightPanel() {
  const col4Content = useUIStore((s) => s.col4Content);
  const closeCol4 = useUIStore((s) => s.closeCol4);
  const rightPanelTab = useUIStore((s) => s.rightPanelTab);
  const setRightPanelTab = useUIStore((s) => s.setRightPanelTab);
  const activeInspirationId = useInspirationStore((s) => s.activeId);

  // Team data
  const teamMembers = useAgentStore((s) => s.teamMembers);
  const templatePool = useAgentStore((s) => s.templatePool);
  const fetchTeam = useAgentStore((s) => s.fetchTeam);
  const fetchTemplatePool = useAgentStore((s) => s.fetchTemplatePool);
  const addToTeam = useAgentStore((s) => s.addToTeam);
  const updateModel = useAgentStore((s) => s.updateModel);
  const removeFromTeam = useAgentStore((s) => s.removeFromTeam);

  const configs = useLLMStore((s) => s.configs);
  const fetchLLM = useLLMStore((s) => s.fetchAll);

  // Brainstorm data
  const brainstormSessions = useBrainstormStore((s) => s.sessions);
  const brainstormActiveId = useBrainstormStore((s) => s.activeId);
  const brainstormFetchAll = useBrainstormStore((s) => s.fetchAll);
  const brainstormSetActive = useBrainstormStore((s) => s.setActive);
  const brainstormActivateSession = useBrainstormStore((s) => s.activateSession);
  const brainstormEndSession = useBrainstormStore((s) => s.endSession);

  useEffect(() => {
    if (col4Content === "team" && activeInspirationId) {
      fetchTeam(activeInspirationId);
      fetchTemplatePool();
      fetchLLM();
    }
  }, [col4Content, activeInspirationId]);

  useEffect(() => {
    if (rightPanelTab === "brainstorm" && activeInspirationId) {
      brainstormFetchAll(activeInspirationId);
    }
  }, [rightPanelTab, activeInspirationId]);

  const availableTemplates = useMemo(() => {
    const inTeamIds = new Set(
      teamMembers.map((m) => m.template_id).filter(Boolean)
    );
    return templatePool.filter((t) => !inTeamIds.has(t.id));
  }, [teamMembers, templatePool]);

  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
        setAddMenuOpen(false);
      }
    };
    if (addMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [addMenuOpen]);

  // Brainstorm search state
  const [bsSearchQuery, setBsSearchQuery] = useState("");
  const [bsSearchOpen, setBsSearchOpen] = useState(false);
  const bsSearchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (bsSearchRef.current && !bsSearchRef.current.contains(e.target as Node)) {
        setBsSearchOpen(false);
      }
    };
    if (bsSearchOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [bsSearchOpen]);

  const bsSearchResults = useMemo(() => {
    if (!bsSearchQuery.trim()) return brainstormSessions;
    const q = bsSearchQuery.trim().replace(/^#/, "");
    const num = parseInt(q, 10);
    if (!isNaN(num)) {
      return brainstormSessions.filter(
        (s) => sessionNum(brainstormSessions, s.id) === num
      );
    }
    return brainstormSessions.filter((s) =>
      s.title.toLowerCase().includes(q.toLowerCase())
    );
  }, [bsSearchQuery, brainstormSessions]);

  // ---- Status panel (no tabs) ----
  if (col4Content === "status") {
    return (
      <div className="rightpanel">
        <div className="rightpanel__header">
          <span className="rightpanel__title">Status</span>
          <button className="rightpanel__close-btn" onClick={closeCol4} title="Close">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="rightpanel__body">
          <div className="rightpanel__content">
            <h3 className="rightpanel__section-title">Activity</h3>
            <p className="rightpanel__placeholder">Status feed and logs — coming in a future update</p>
          </div>
        </div>
      </div>
    );
  }

  // ---- Tab bar header (Team | Brainstorm) ----
  const showTabs = col4Content !== null;

  return (
    <div className="rightpanel">
      <div className="rightpanel__header">
        {showTabs && (
          <div className="rightpanel__tab-bar">
            <button
              className={`rightpanel__tab${rightPanelTab === "team" ? " rightpanel__tab--active" : ""}`}
              onClick={() => setRightPanelTab("team")}
            >
              Team
            </button>
            <button
              className={`rightpanel__tab${rightPanelTab === "brainstorm" ? " rightpanel__tab--active" : ""}`}
              onClick={() => setRightPanelTab("brainstorm")}
            >
              Brainstorm
            </button>
          </div>
        )}
        {!showTabs && <span className="rightpanel__title" />}
        <button className="rightpanel__close-btn" onClick={closeCol4} title="Close">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <div className="rightpanel__body">
        {/* ---- Team Tab ---- */}
        {rightPanelTab === "team" && (
          <div className="rightpanel__content">
            {!activeInspirationId ? (
              <p className="rightpanel__placeholder">Select an Inspiration to manage its team</p>
            ) : (
              <>
                <div className="rp-section-header">
                  <span className="rightpanel__section-title">AGENTS</span>
                  <span className="rp-badge">{teamMembers.length}</span>
                </div>

                {teamMembers.length === 0 && (
                  <p className="rightpanel__placeholder">No agents in team yet</p>
                )}

                {teamMembers.map((member) => {
                  const color = ROLE_COLOR[member.role] ?? "#94A3B8";
                  const isLead = member.role === "lead";
                  const defaultCfg = configs.find((c) => c.is_default);
                  const effectiveModel = member.model || (isLead && defaultCfg ? `${defaultCfg.provider} · ${defaultCfg.model}` : "");

                  return (
                    <div key={member.id} className="rp-agent-card">
                      <div className="rp-agent-card__top">
                        <div
                          className="rp-agent-card__avatar"
                          style={{ background: `${color}22`, borderColor: `${color}44` }}
                        >
                          <span style={{ color }}>{member.name.slice(0, 1).toUpperCase()}</span>
                        </div>
                        <div className="rp-agent-card__info">
                          <div className="rp-agent-card__name">{member.name}</div>
                          <div className="rp-agent-card__role">{member.role}</div>
                        </div>
                        <span className={`rp-status-dot ${member.status === "working" ? "rp-status-dot--active" : ""}`} />
                      </div>

                      <div className="rp-agent-card__controls">
                        <select
                          className="rp-model-select"
                          value={effectiveModel}
                          onChange={(e) => {
                            if (e.target.value) updateModel(member.id, e.target.value);
                          }}
                          title="Select model"
                        >
                          {!effectiveModel && <option value="" disabled>No model</option>}
                          {configs.map((c) => {
                            const value = `${c.provider} · ${c.model}`;
                            return <option key={c.id} value={value}>{c.provider} · {c.model}</option>;
                          })}
                        </select>

                        {!isLead && (
                          <button
                            className="rp-remove-btn"
                            onClick={() => removeFromTeam(member.inspiration_id, member.id)}
                            title="Remove from team"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}

                {activeInspirationId && availableTemplates.length > 0 && (
                  <div className="rp-divider">
                    <span>Agents</span>
                    <div className="rp-add-dropdown" ref={addMenuRef}>
                      <button
                        className="rp-add-trigger"
                        onClick={() => setAddMenuOpen((v) => !v)}
                      >
                        + Add
                      </button>
                      {addMenuOpen && (
                        <div className="rp-add-menu">
                          {availableTemplates.map((t) => {
                            const color = ROLE_COLOR[t.role] ?? "#94A3B8";
                            return (
                              <div
                                key={t.id}
                                className="rp-add-menu-item"
                                onClick={() => {
                                  if (activeInspirationId) addToTeam(activeInspirationId, t.id);
                                  setAddMenuOpen(false);
                                }}
                              >
                                <div
                                  className="rp-agent-card__avatar rp-add-menu-avatar"
                                  style={{ background: `${color}22`, borderColor: `${color}44` }}
                                >
                                  <span style={{ color }}>{t.name.slice(0, 1).toUpperCase()}</span>
                                </div>
                                <div className="rp-add-menu-info">
                                  <div className="rp-add-menu-name">{t.name}</div>
                                  <div className="rp-add-menu-role">{t.role}</div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ---- Brainstorm Tab ---- */}
        {rightPanelTab === "brainstorm" && (
          <div className="rightpanel__content">
            {!activeInspirationId ? (
              <p className="rightpanel__placeholder">Select an Inspiration to view brainstorm sessions</p>
            ) : (
              <>
                {/* Search box */}
                <div className="bs-search" ref={bsSearchRef}>
                  <div className="bs-search__box">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      className="bs-search__input"
                      type="text"
                      placeholder="Search by #number or title..."
                      value={bsSearchQuery}
                      onChange={(e) => { setBsSearchQuery(e.target.value); setBsSearchOpen(true); }}
                      onFocus={() => setBsSearchOpen(true)}
                      onKeyDown={(e) => { if (e.key === "Escape") { setBsSearchOpen(false); (e.target as HTMLInputElement).blur(); } }}
                    />
                  </div>
                  {bsSearchOpen && bsSearchQuery.trim() && (
                    <div className="bs-search__dropdown">
                      {bsSearchResults.length === 0 ? (
                        <div className="bs-search__empty">No matching sessions</div>
                      ) : (
                        bsSearchResults.slice(0, 8).map((s) => {
                          const num = sessionNum(brainstormSessions, s.id);
                          const isActive = s.id === brainstormActiveId;
                          return (
                            <button
                              key={s.id}
                              className={`bs-search__item${isActive ? " bs-search__item--active" : ""}`}
                              onClick={() => {
                                brainstormSetActive(s.id);
                                setBsSearchOpen(false);
                                setBsSearchQuery("");
                              }}
                            >
                              <span className="bs-search__item-num">#{num}</span>
                              <span className="bs-search__item-title">{s.title}</span>
                              <span className={`bs-search__item-status bs-search__item-status--${s.status}`}>{s.status}</span>
                            </button>
                          );
                        })
                      )}
                    </div>
                  )}
                </div>

                {/* Active session detail or empty state */}
                {brainstormActiveId ? (() => {
                  const session = brainstormSessions.find((s) => s.id === brainstormActiveId);
                  if (!session) return null;
                  const num = sessionNum(brainstormSessions, session.id);
                  return (
                    <div className="bs-card">
                      {/* Hero — accent header */}
                      <div className="bs-card__hero">
                        <div className="bs-card__hero-top">
                          <div className="bs-card__hero-left">
                            <span className="bs-card__num-badge">#{num}</span>
                            <span className="bs-card__title">{session.title}</span>
                          </div>
                          <button
                            className={`bs-toggle${session.status === "active" ? " bs-toggle--active" : ""}`}
                            title={session.status === "active" ? "Deactivate session" : "Activate session"}
                            onClick={() => {
                              if (session.status === "active") {
                                brainstormEndSession(session.id);
                              } else {
                                brainstormActivateSession(session.id);
                              }
                            }}
                          >
                            <span className="bs-toggle__knob" />
                          </button>
                        </div>
                        <div className="bs-card__meta-row">
                          <span>{formatTime(session.created_at)}</span>
                          {session.ended_at && (
                            <>
                              <span className="bs-card__meta-dot" />
                              <span>Ended {formatTime(session.ended_at)}</span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Body — scrollable sections */}
                      <div className="bs-card__body">
                        {/* Sandbox */}
                        <div className="bs-card__section">
                          <h4 className="bs-card__label">Sandbox</h4>
                          <div className="bs-card__path">
                            <svg className="bs-card__path-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                            </svg>
                            <span>{session.sandbox_path}</span>
                          </div>
                        </div>

                        {/* Settings */}
                        <div className="bs-card__section">
                          <h4 className="bs-card__label">Configuration</h4>
                          <div className="bs-card__grid">
                            <div className="bs-card__field">
                              <span className="bs-card__key">Max Messages</span>
                              <span className="bs-card__value">{session.max_messages}</span>
                            </div>
                            <div className="bs-card__field">
                              <span className="bs-card__key">Cooldown</span>
                              <span className="bs-card__value">{session.cooldown_seconds}s</span>
                            </div>
                            <div className="bs-card__field">
                              <span className="bs-card__key">Messages</span>
                              <span className="bs-card__value">{session.message_count}</span>
                            </div>
                            <div className="bs-card__field">
                              <span className="bs-card__key">Status</span>
                              <span className="bs-card__value" style={{ color: session.status === "active" ? "#16a34a" : "#94a3b8" }}>
                                {session.status}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Files */}
                        <div className="bs-card__section">
                          <h4 className="bs-card__label">Files ({session.file_tree.length})</h4>
                          {session.file_tree.length > 0 ? (
                            <ul className="bs-card__file-list">
                              {session.file_tree.map((f) => (
                                <li key={f.path} className="bs-card__file">
                                  <span className="bs-card__file-icon">{f.type === "directory" ? "\u{1F4C1}" : "\u{1F4C4}"}</span>
                                  <span className="bs-card__file-name">{f.name}</span>
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <p className="bs-card__empty">No files generated yet.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })() : (
                  <div className="bs-empty">
                    <div className="bs-empty__icon-wrap">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                      </svg>
                    </div>
                    <p className="bs-empty__title">No active session</p>
                    <p className="bs-empty__subtitle">Start a brainstorm from the chat input<br />to see session details here</p>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
