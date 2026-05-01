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
  const [addSearchQuery, setAddSearchQuery] = useState("");
  const addMenuRef = useRef<HTMLDivElement>(null);

  const [modelDropdownId, setModelDropdownId] = useState<string | null>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target as Node)) {
        setAddMenuOpen(false);
      }
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setModelDropdownId(null);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

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
          <button className="rightpanel__close-btn" onClick={closeCol4} data-tooltip-bottom="Close">
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
        <button className="rightpanel__close-btn" onClick={closeCol4} data-tooltip-bottom="Close">
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

                {teamMembers.map((member, index) => {
                  const color = ROLE_COLOR[member.role] ?? "#94A3B8";
                  const isLead = member.role === "lead";
                  const defaultCfg = configs.find((c) => c.is_default);
                  const effectiveModel = member.model || (isLead && defaultCfg ? `${defaultCfg.provider} · ${defaultCfg.model}` : "");
                  const isDropdownOpen = modelDropdownId === member.id;
                  const currentLabel = effectiveModel || "Select model";
                  const num = index + 1;

                  return (
                    <div key={member.id} className="rp-agent-card">
                      <div className="rp-agent-card__top">
                        <div
                          className="rp-agent-card__avatar"
                          style={{ background: `${color}22` }}
                        >
                          <span style={{ color }}>{num}</span>
                        </div>
                        <div className="rp-agent-card__info">
                          <div className="rp-agent-card__name">{member.name}</div>
                          <div className="rp-agent-card__role">{member.role}</div>
                        </div>
                        <span className={`rp-status-badge${member.status === "working" ? " rp-status-badge--working" : ""}`}>
                          <span className="rp-status-badge__dot" />
                          {member.status === "working" ? "Working" : "Idle"}
                        </span>
                      </div>

                      <div className="rp-agent-card__controls">
                        <div className="rp-model-dropdown" ref={isDropdownOpen ? modelDropdownRef : undefined}>
                          <button
                            className={`rp-model-trigger${!effectiveModel ? " rp-model-trigger--empty" : ""}`}
                            onClick={() => setModelDropdownId(isDropdownOpen ? null : member.id)}
                            data-tooltip="Select model"
                          >
                            <span className="rp-model-trigger__label">{currentLabel}</span>
                            <svg className={`rp-model-trigger__chevron${isDropdownOpen ? " rp-model-trigger__chevron--open" : ""}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="6 9 12 15 18 9" />
                            </svg>
                          </button>
                          {isDropdownOpen && (
                            <div className="rp-model-popup">
                              {configs.map((c) => {
                                const value = `${c.provider} · ${c.model}`;
                                const isSelected = value === effectiveModel;
                                return (
                                  <div
                                    key={c.id}
                                    className={`rp-model-option${isSelected ? " rp-model-option--selected" : ""}`}
                                    onClick={() => {
                                      updateModel(member.id, value);
                                      setModelDropdownId(null);
                                    }}
                                  >
                                    <span className="rp-model-option__provider">{c.provider}</span>
                                    <span className="rp-model-option__model">{c.model}</span>
                                    {isSelected && (
                                      <svg className="rp-model-option__check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                        <polyline points="20 6 9 17 4 12" />
                                      </svg>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>

                        {!isLead && (
                          <button
                            className="rp-remove-btn"
                            onClick={() => removeFromTeam(member.inspiration_id, member.id)}
                            data-tooltip="Remove from team"
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
                    <div className="rp-add-dropdown" ref={addMenuRef}>
                      <button
                        className="rp-icon-add-btn"
                        onClick={() => {
                          setAddMenuOpen((v) => !v);
                          setAddSearchQuery("");
                        }}
                        data-tooltip="Add agent to team"
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <line x1="12" y1="5" x2="12" y2="19" />
                          <line x1="5" y1="12" x2="19" y2="12" />
                        </svg>
                      </button>
                      {addMenuOpen && (
                        <div className="rp-add-menu">
                          <div className="rp-add-menu__search">
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <circle cx="11" cy="11" r="8" />
                              <line x1="21" y1="21" x2="16.65" y2="16.65" />
                            </svg>
                            <input
                              className="rp-add-menu__search-input"
                              type="text"
                              placeholder="Search agents..."
                              value={addSearchQuery}
                              onChange={(e) => setAddSearchQuery(e.target.value)}
                              autoFocus
                            />
                          </div>
                          <div className="rp-add-menu__list">
                            {availableTemplates
                              .filter((t) => {
                                if (!addSearchQuery.trim()) return true;
                                const q = addSearchQuery.toLowerCase();
                                return t.name.toLowerCase().includes(q) || t.role.toLowerCase().includes(q);
                              })
                              .map((t) => {
                                const color = ROLE_COLOR[t.role] ?? "#94A3B8";
                                return (
                                  <div
                                    key={t.id}
                                    className="rp-add-menu-item"
                                    onClick={() => {
                                      if (activeInspirationId) addToTeam(activeInspirationId, t.id);
                                      setAddMenuOpen(false);
                                      setAddSearchQuery("");
                                    }}
                                  >
                                    <div
                                      className="rp-agent-card__avatar rp-add-menu-avatar"
                                      style={{ background: `${color}22` }}
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
                            {availableTemplates.filter((t) => {
                              const q = addSearchQuery.toLowerCase();
                              return t.name.toLowerCase().includes(q) || t.role.toLowerCase().includes(q);
                            }).length === 0 && (
                              <div className="rp-add-menu__empty">No matching agents</div>
                            )}
                          </div>
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
                              <span className="bs-search__item-num">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                                </svg>
                              </span>
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
                  return (
                    <div className="bs-card">
                      {/* Hero — accent header */}
                      <div className="bs-card__hero">
                        <div className="bs-card__hero-top">
                          <div className="bs-card__hero-left">
                            <span className="bs-card__num-badge">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                              </svg>
                            </span>
                            <span className="bs-card__title">{session.title}</span>
                          </div>
                          <div className="bs-toggle-wrap">
                            <button
                              className={`bs-toggle${session.status === "active" ? " bs-toggle--active" : ""}`}
                              role="switch"
                              aria-checked={session.status === "active"}
                              aria-label={session.status === "active" ? "Deactivate session" : "Activate session"}
                              data-tooltip={session.status === "active" ? "Deactivate session" : "Activate session"}
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
                        <div className="bs-section">
                          <div className="bs-section__header">
                            <span className="bs-section__icon">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                                <polyline points="9 3 9 21" />
                              </svg>
                            </span>
                            <h4 className="bs-section__title">Sandbox</h4>
                          </div>
                          <div className="bs-section__body">
                            <div className="bs-card__path">
                              <svg className="bs-card__path-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                              </svg>
                              <span className="bs-card__path-text">{session.sandbox_path}</span>
                            </div>
                          </div>
                        </div>

                        {/* Configuration */}
                        <div className="bs-section">
                          <div className="bs-section__header">
                            <span className="bs-section__icon">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <circle cx="12" cy="12" r="3" />
                                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                              </svg>
                            </span>
                            <h4 className="bs-section__title">Configuration</h4>
                          </div>
                          <div className="bs-section__body">
                            <div className="bs-card__config-list">
                              <div className="bs-card__config-row">
                                <span className="bs-card__config-key">Max Messages</span>
                                <span className="bs-card__config-value">{session.max_messages}</span>
                              </div>
                              <div className="bs-card__config-row">
                                <span className="bs-card__config-key">Cooldown</span>
                                <span className="bs-card__config-value">{session.cooldown_seconds}s</span>
                              </div>
                              <div className="bs-card__config-row">
                                <span className="bs-card__config-key">Messages Used</span>
                                <span className="bs-card__config-value">{session.message_count}</span>
                              </div>
                              <div className="bs-card__config-row">
                                <span className="bs-card__config-key">Status</span>
                                <span className={`bs-card__config-value${session.status === "active" ? " bs-card__config-value--active" : " bs-card__config-value--ended"}`}>
                                  {session.status}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>

                        {/* Files */}
                        <div className="bs-section">
                          <div className="bs-section__header">
                            <span className="bs-section__icon">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                <polyline points="14 2 14 8 20 8" />
                                <line x1="16" y1="13" x2="8" y2="13" />
                                <line x1="16" y1="17" x2="8" y2="17" />
                                <polyline points="10 9 9 9 8 9" />
                              </svg>
                            </span>
                            <h4 className="bs-section__title">Files</h4>
                            {session.file_tree.length > 0 && (
                              <span className="bs-card__config-value" style={{ marginLeft: "auto", fontSize: "11px", color: "var(--text-muted)" }}>{session.file_tree.length}</span>
                            )}
                          </div>
                          <div className="bs-section__body">
                            {session.file_tree.length > 0 ? (
                              <ul className="bs-card__file-list">
                                {session.file_tree.map((f) => (
                                  <li key={f.path} className="bs-card__file">
                                    <span className="bs-card__file-icon">
                                      {f.type === "directory" ? (
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
                                        </svg>
                                      ) : (
                                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                          <polyline points="14 2 14 8 20 8" />
                                        </svg>
                                      )}
                                    </span>
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
                    </div>
                  );
                })() : (
                  <div className="bs-empty">
                    <div className="bs-empty__icon-wrap">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--bs-purple)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
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
