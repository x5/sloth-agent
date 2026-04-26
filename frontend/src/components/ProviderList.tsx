import { useEffect, useState } from "react";
import { useLLMStore } from "../stores/llmStore";
import { ProviderIcon } from "./ProviderIcon";

export default function ProviderList() {
  const { configs, activeId, loading, fetchAll, setActive } = useLLMStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAll().catch((e) => setError(String(e)));
  }, []);

  // Auto-select first config
  useEffect(() => {
    if (!activeId && configs.length > 0) {
      setActive(configs[0].id);
    }
  }, [configs, activeId]);

  return (
    <div className="provider-list">
      <div className="provider-list__body">
        {error && (
          <div className="llm-error-bar" style={{ borderBottom: "none", borderTop: "1px solid #fecaca" }}>
            {error}
            <button className="projectlist__empty-btn" onClick={() => { setError(null); fetchAll().catch((e) => setError(String(e))); }}>
              Retry
            </button>
          </div>
        )}

        {loading && configs.length === 0 && (
          <div className="projectlist__empty">Loading...</div>
        )}
        {!loading && configs.length === 0 && (
          <div className="projectlist__empty" style={{ padding: "20px 12px" }}>
            <p style={{ fontSize: 13 }}>No providers yet</p>
          </div>
        )}

        {configs.map((c) => {
          const isActive = c.id === activeId;
          return (
            <div
              key={c.id}
              className={`llm-provider-card${isActive ? " llm-provider-card--active" : ""}`}
              onClick={() => setActive(c.id)}
            >
              <div className="llm-provider-card__icon">
                <ProviderIcon provider={c.provider} />
              </div>
              <div className="llm-provider-card__body">
                <div className="llm-provider-card__row">
                  <div className="llm-provider-card__name">{c.provider}</div>
                  {c.is_default && (
                    <span className="llm-provider-card__badge">DEFAULT</span>
                  )}
                </div>
                <div className="llm-provider-card__model">{c.model}</div>
              </div>
              {isActive && <div className="projectlist__item-accent" />}
            </div>
          );
        })}
      </div>

      {/* Add Provider — at bottom */}
      <div className="provider-list__footer">
        <ProviderAddForm />
      </div>
    </div>
  );
}

/* ---- Inline Add Form ---- */
function ProviderAddForm() {
  const create = useLLMStore((s) => s.create);
  const [show, setShow] = useState(false);
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiFormat, setApiFormat] = useState("openai");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAdd = async () => {
    if (!provider.trim() || !model.trim() || !apiKey.trim() || !baseUrl.trim()) return;
    setAdding(true);
    setError(null);
    try {
      await create({
        provider: provider.trim(),
        model: model.trim(),
        api_key: apiKey.trim(),
        base_url: baseUrl.trim(),
        api_format: apiFormat,
      });
      setShow(false);
      setProvider("");
      setModel("");
      setApiKey("");
      setBaseUrl("");
      setApiFormat("openai");
    } catch (e) {
      setError(String(e));
    }
    setAdding(false);
  };

  if (!show) {
    return (
      <button className="llm-provider-add-btn" onClick={() => setShow(true)} title="Add Provider">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    );
  }

  return (
    <div className="provider-add-form">
      <h4 className="provider-add-form__title">Add Provider</h4>
      {error && <div style={{ color: "#e74c3c", fontSize: 12, marginBottom: 8 }}>{error}</div>}
      <input className="settings-form__input" type="text" value={provider} onChange={(e) => setProvider(e.target.value)} placeholder="Provider name" />
      <input className="settings-form__input" type="text" value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model (e.g. deepseek-v4-pro)" />
      <input className="settings-form__input" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="API Key" />
      <input className="settings-form__input" type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="Base URL" />
      <select className="settings-form__select" value={apiFormat} onChange={(e) => setApiFormat(e.target.value)}>
        <option value="openai">OpenAI Compatible</option>
        <option value="anthropic">Anthropic</option>
      </select>
      <div className="settings-form__actions">
        <button className="settings-form__save-btn" onClick={handleAdd} disabled={adding}>
          {adding ? "Adding..." : "Add"}
        </button>
        <button className="settings-form__cancel-btn" onClick={() => setShow(false)}>Cancel</button>
      </div>
    </div>
  );
}
