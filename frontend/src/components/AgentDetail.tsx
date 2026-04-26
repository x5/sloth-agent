import { useEffect, useState } from "react";
import { useAgentPoolStore } from "../stores/agentPoolStore";
import { useLLMStore } from "../stores/llmStore";
import { ProviderIcon } from "./ProviderIcon";
import SystemPromptView from "./SystemPromptView";

export default function AgentDetail() {
  const { templates, activeId, update } = useAgentPoolStore();
  const configs = useLLMStore((s) => s.configs);
  const fetchLLM = useLLMStore((s) => s.fetchAll);
  const template = templates.find((t) => t.id === activeId);

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [defaultModel, setDefaultModel] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [autoJoin, setAutoJoin] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLLM().catch(() => {});
  }, []);

  useEffect(() => {
    if (template) {
      setName(template.name);
      setDefaultModel(template.default_model);
      setSystemPrompt(template.system_prompt);
      setAutoJoin(template.auto_join);
      setEditing(false);
    }
  }, [template]);

  if (!template) {
    return (
      <div className="detail">
        <div className="detail__empty">
          <p className="chatarea__empty-text">Select an agent to view details</p>
        </div>
      </div>
    );
  }

  const isLead = template.role === "lead";
  const defaultCfg = configs.find((c) => c.is_default);
  const effectiveModel = defaultModel || (defaultCfg ? `${defaultCfg.provider} · ${defaultCfg.model}` : "");
  const selectedConfig = configs.find((c) => `${c.provider} · ${c.model}` === effectiveModel);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await update(template.id, {
        name,
        default_model: defaultModel,
        system_prompt: systemPrompt,
        auto_join: autoJoin,
      });
      setEditing(false);
    } catch (e) {
      setError(String(e));
    }
    setSaving(false);
  };

  const handleCancelEdit = () => {
    setName(template.name);
    setDefaultModel(template.default_model);
    setSystemPrompt(template.system_prompt);
    setAutoJoin(template.auto_join);
    setEditing(false);
    setError(null);
  };

  return (
    <div className="detail">
      {/* Topbar */}
      <div className="detail__topbar">
        <div className="detail__topbar-title">{template.name}</div>
        <div className="detail__topbar-actions">
          <button
            className="detail__icon-btn"
            onClick={() => setEditing(true)}
            title="Edit"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
        </div>
      </div>

      {error && (
        <div className="llm-error-bar" style={{ borderRadius: "var(--radius-sm)" }}>
          {error}
        </div>
      )}

      {/* Read-only view */}
      {!editing && (
        <div className="detail__body">
          <div className="detail-field">
            <span className="detail-field__label">Role</span>
            <span className="detail-field__value">{template.role}</span>
          </div>
          <div className="detail-field">
            <span className="detail-field__label">LLM Provider</span>
            <span className="detail-field__value">
              {selectedConfig ? (
                <span className="agent-detail__provider-ref">
                  <span className="agent-detail__provider-ref-icon">
                    <ProviderIcon provider={selectedConfig.provider} />
                  </span>
                  {selectedConfig.provider} · {selectedConfig.model}
                </span>
              ) : (
                <span style={{ color: "var(--text-muted)" }}>Not configured</span>
              )}
            </span>
          </div>
          <div className="detail-field">
            <span className="detail-field__label">Auto-join</span>
            <span className="detail-field__value">{template.auto_join ? "Yes" : "No"}</span>
          </div>
          <div className="detail-field detail-field--top">
            <span className="detail-field__label">System Prompt</span>
            <SystemPromptView text={template.system_prompt} />
          </div>
        </div>
      )}

      {/* Edit form */}
      {editing && (
        <div className="detail__body">
          <div className="detail-field">
            <span className="detail-field__label">Name</span>
            <input
              className="detail-field__input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isLead}
            />
          </div>

          <div className="detail-field">
            <span className="detail-field__label">LLM Provider</span>
            <div className="agent-detail__provider-select">
              {configs.map((c) => {
                const value = `${c.provider} · ${c.model}`;
                const isSelected = value === defaultModel;
                return (
                  <div
                    key={c.id}
                    className={`agent-detail__provider-option${isSelected ? " agent-detail__provider-option--selected" : ""}`}
                    onClick={() => setDefaultModel(value)}
                  >
                    <span className="agent-detail__provider-option-icon">
                      <ProviderIcon provider={c.provider} />
                    </span>
                    <span className="agent-detail__provider-option-name">{c.provider}</span>
                    <span className="agent-detail__provider-option-model">{c.model}</span>
                  </div>
                );
              })}
              {configs.length === 0 && (
                <div className="agent-detail__provider-empty">
                  No providers configured. Add one in Settings.
                </div>
              )}
            </div>
          </div>

          <div className="detail-field detail-field--top">
            <span className="detail-field__label">System Prompt</span>
            <textarea
              className="detail-field__textarea"
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              rows={16}
            />
          </div>

          <div className="detail-field">
            <span className="detail-field__label">Auto-join</span>
            <label className="settings-form__checkbox-label" style={{ margin: 0 }}>
              <input
                type="checkbox"
                checked={autoJoin}
                onChange={(e) => setAutoJoin(e.target.checked)}
                disabled={isLead}
              />
              <span>Auto-join new Inspirations</span>
            </label>
          </div>

          <div className="detail__form-actions">
            <button className="detail__save-btn" onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button className="detail__cancel-btn" onClick={handleCancelEdit}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
