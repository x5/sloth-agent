import { useEffect, useState } from "react";
import { useLLMStore } from "../stores/llmStore";

export default function ProviderDetail() {
  const { configs, activeId, update, remove, setDefault } = useLLMStore();
  const activeConfig = configs.find((c) => c.id === activeId);

  // ---- Edit mode ----
  const [editing, setEditing] = useState(false);
  const [editProvider, setEditProvider] = useState("");
  const [editModel, setEditModel] = useState("");
  const [editApiKey, setEditApiKey] = useState("");
  const [editBaseUrl, setEditBaseUrl] = useState("");
  const [editApiFormat, setEditApiFormat] = useState("openai");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeConfig) {
      setEditProvider(activeConfig.provider);
      setEditModel(activeConfig.model);
      setEditApiKey(activeConfig.api_key);
      setEditBaseUrl(activeConfig.base_url);
      setEditApiFormat(activeConfig.api_format);
      setEditing(false);
    }
  }, [activeConfig]);

  // ---- No selection ----
  if (!activeConfig) {
    return (
      <div className="detail">
        <div className="detail__empty">
          <p className="chatarea__empty-text">Select a provider to view details</p>
        </div>
      </div>
    );
  }

  // ---- Handlers ----
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await update(activeConfig.id, {
        provider: editProvider,
        model: editModel,
        api_key: editApiKey.includes("****") ? undefined : editApiKey,
        base_url: editBaseUrl,
        api_format: editApiFormat,
      });
      setEditing(false);
    } catch (e) {
      setError(String(e));
    }
    setSaving(false);
  };

  const handleCancelEdit = () => {
    setEditProvider(activeConfig.provider);
    setEditModel(activeConfig.model);
    setEditApiKey(activeConfig.api_key);
    setEditBaseUrl(activeConfig.base_url);
    setEditApiFormat(activeConfig.api_format);
    setEditing(false);
    setError(null);
  };

  const handleDelete = async () => {
    if (activeConfig.is_default) {
      alert("Cannot delete the default LLM provider.");
      return;
    }
    if (!confirm(`Delete "${activeConfig.provider}"?`)) return;
    try {
      await remove(activeConfig.id);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSetDefault = async () => {
    try {
      await setDefault(activeConfig.id);
    } catch (e) {
      setError(String(e));
    }
  };

  return (
    <div className="detail">
      {/* Topbar */}
      <div className="detail__topbar">
        <div className="detail__topbar-title">{activeConfig.provider}</div>
        <div className="detail__topbar-actions">
          {activeConfig.is_default && <span className="detail__badge">DEFAULT</span>}
          {!activeConfig.is_default && (
            <button className="detail__icon-btn" onClick={handleSetDefault} title="Set as default">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
            </button>
          )}
          <button className="detail__icon-btn" onClick={() => setEditing(true)} title="Edit">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button className="detail__icon-btn detail__icon-btn--danger" onClick={handleDelete} title="Delete">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
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
            <span className="detail-field__label">Provider</span>
            <span className="detail-field__value">{activeConfig.provider}</span>
          </div>
          <div className="detail-field">
            <span className="detail-field__label">Model</span>
            <span className="detail-field__value">{activeConfig.model}</span>
          </div>
          <div className="detail-field">
            <span className="detail-field__label">API Key</span>
            <span className="detail-field__value">{activeConfig.api_key}</span>
          </div>
          <div className="detail-field">
            <span className="detail-field__label">Base URL</span>
            <span className="detail-field__value">{activeConfig.base_url}</span>
          </div>
          <div className="detail-field">
            <span className="detail-field__label">API Format</span>
            <span className="detail-field__value">
              {activeConfig.api_format === "openai" ? "OpenAI Compatible" : "Anthropic"}
            </span>
          </div>
        </div>
      )}

      {/* Edit form */}
      {editing && (
        <div className="detail__body">
          <div className="detail-field">
            <span className="detail-field__label">Provider</span>
            <input className="detail-field__input" type="text" value={editProvider} onChange={(e) => setEditProvider(e.target.value)} />
          </div>
          <div className="detail-field">
            <span className="detail-field__label">Model</span>
            <input className="detail-field__input" type="text" value={editModel} onChange={(e) => setEditModel(e.target.value)} />
          </div>
          <div className="detail-field">
            <span className="detail-field__label">API Key</span>
            <input className="detail-field__input" type="password" value={editApiKey} onChange={(e) => setEditApiKey(e.target.value)} placeholder="sk-..." />
          </div>
          <div className="detail-field">
            <span className="detail-field__label">Base URL</span>
            <input className="detail-field__input" type="text" value={editBaseUrl} onChange={(e) => setEditBaseUrl(e.target.value)} />
          </div>
          <div className="detail-field">
            <span className="detail-field__label">API Format</span>
            <select className="detail-field__input" value={editApiFormat} onChange={(e) => setEditApiFormat(e.target.value)} style={{ height: 32 }}>
              <option value="openai">OpenAI Compatible</option>
              <option value="anthropic">Anthropic</option>
            </select>
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
