import { useEffect, useMemo, useRef, useState } from "react";
import { useUIStore } from "../stores/uiStore";
import { useInspirationStore } from "../stores/inspirationStore";
import { useAgentStore } from "../stores/agentStore";
import { useLLMStore } from "../stores/llmStore";

const ROLE_COLOR: Record<string, string> = {
  lead: "#8B5CF6",
  fortune: "#06B6D4",
};

export default function RightPanel() {
  const col4Content = useUIStore((s) => s.col4Content);
  const closeCol4 = useUIStore((s) => s.closeCol4);
  const activeInspirationId = useInspirationStore((s) => s.activeId);

  const teamMembers = useAgentStore((s) => s.teamMembers);
  const templatePool = useAgentStore((s) => s.templatePool);
  const fetchTeam = useAgentStore((s) => s.fetchTeam);
  const fetchTemplatePool = useAgentStore((s) => s.fetchTemplatePool);
  const addToTeam = useAgentStore((s) => s.addToTeam);
  const updateModel = useAgentStore((s) => s.updateModel);
  const removeFromTeam = useAgentStore((s) => s.removeFromTeam);

  const configs = useLLMStore((s) => s.configs);
  const fetchLLM = useLLMStore((s) => s.fetchAll);

  useEffect(() => {
    if (col4Content === "team" && activeInspirationId) {
      fetchTeam(activeInspirationId);
      fetchTemplatePool();
      fetchLLM();
    }
  }, [col4Content, activeInspirationId]);

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

  if (col4Content !== "team") {
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

  if (!activeInspirationId) {
    return (
      <div className="rightpanel">
        <div className="rightpanel__header">
          <span className="rightpanel__title">Team</span>
          <button className="rightpanel__close-btn" onClick={closeCol4} title="Close">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="rightpanel__body">
          <div className="rightpanel__content">
            <p className="rightpanel__placeholder">Select an Inspiration to manage its team</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rightpanel">
      <div className="rightpanel__header">
        <span className="rightpanel__title">Team</span>
        <button className="rightpanel__close-btn" onClick={closeCol4} title="Close">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      <div className="rightpanel__body">
        <div className="rightpanel__content">
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

          {availableTemplates.length > 0 && (
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
        </div>
      </div>
    </div>
  );
}
