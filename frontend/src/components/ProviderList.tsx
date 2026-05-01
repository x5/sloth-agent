import { useEffect, useRef, useState } from "react";
import { useLLMStore } from "../stores/llmStore";
import { ProviderIcon } from "./ProviderIcon";
import { PROVIDER_PRESETS, API_FORMATS } from "../shared/providerPresets";

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
                    <span className="llm-provider-card__dot" data-tooltip="Default provider" />
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

function validateUrl(v: string): string | null {
  if (!v.trim()) return "Base URL is required";
  if (!/^https?:\/\/.+/.test(v.trim())) return "Must start with http:// or https://";
  return null;
}

function validateApiKey(v: string): string | null {
  if (!v.trim()) return "API Key is required";
  if (v.trim().length < 12) return "API Key must be at least 12 characters";
  return null;
}

function validateModel(v: string): string | null {
  if (!v.trim()) return "Model is required";
  return null;
}

function ProviderAddForm() {
  const create = useLLMStore((s) => s.create);
  const [show, setShow] = useState(false);
  const [presetKey, setPresetKey] = useState("");
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiFormat, setApiFormat] = useState("openai");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Field errors
  const [errors, setErrors] = useState<Record<string, string | null>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const validate = () => {
    const errs: Record<string, string | null> = {
      provider: provider.trim() ? null : "Provider is required",
      model: validateModel(model),
      apiKey: validateApiKey(apiKey),
      baseUrl: validateUrl(baseUrl),
    };
    setErrors(errs);
    return !Object.values(errs).some(Boolean);
  };

  const handleAdd = async () => {
    setTouched({ provider: true, model: true, apiKey: true, baseUrl: true });
    if (!validate()) return;
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
      setPresetKey("");
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
      <button className="llm-provider-add-btn" onClick={() => setShow(true)} data-tooltip="Add Provider">
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
      {error && <div className="provider-add-form__error">{error}</div>}

      {/* Provider — autocomplete */}
      <div className="provider-add-field">
        <label className="provider-add-field__label">Provider</label>
        <Autocomplete
          suggestions={[
            ...PROVIDER_PRESETS.map((p) => ({
              key: p.key,
              label: p.name,
              icon: <ProviderIcon provider={p.name} />,
            })),
            { key: "__sep__", label: "", isSeparator: true },
            { key: "__custom__", label: "Custom...", isAction: true },
          ]}
          value={provider}
          onChange={(v) => { setProvider(v); setTouched((t) => ({ ...t, provider: true })); }}
          onSelect={(item) => {
            if (item.key === "__custom__") {
              setPresetKey("__custom__");
              setBaseUrl("");
              setApiFormat("openai");
            } else {
              const preset = PROVIDER_PRESETS.find((p) => p.key === item.key);
              if (preset) {
                setPresetKey(preset.key);
                setModel("");
                setBaseUrl(preset.base_url);
                setApiFormat(preset.api_format);
              }
            }
          }}
          placeholder="Search or select a provider..."
          hasError={!!(touched.provider && errors.provider)}
          errorHint={errors.provider}
          normalHint="Choose a built-in provider or type 'Custom...'"
        />
      </div>

      {/* Model — autocomplete */}
      <div className="provider-add-field">
        <label className="provider-add-field__label">Model</label>
        <Autocomplete
          suggestions={(presetKey && presetKey !== "__custom__")
            ? (PROVIDER_PRESETS.find((p) => p.key === presetKey)?.models || []).map((m) => ({
                key: m,
                label: m,
              }))
            : []
          }
          value={model}
          onChange={(v) => { setModel(v); setTouched((t) => ({ ...t, model: true })); }}
          placeholder="Search or type a model name..."
          hasError={!!(touched.model && errors.model)}
          errorHint={errors.model}
          normalHint="Choose from list or type your own"
        />
      </div>

      {/* Base URL */}
      <div className="provider-add-field">
        <label className="provider-add-field__label">Base URL</label>
        <input
          className={`provider-add-field__input${touched.baseUrl && errors.baseUrl ? " provider-add-field__input--error" : ""}`}
          type="text"
          value={baseUrl}
          onChange={(e) => { setBaseUrl(e.target.value); setTouched((t) => ({ ...t, baseUrl: true })); }}
          placeholder="https://api.example.com/v1"
        />
        {touched.baseUrl && errors.baseUrl ? (
          <span className="provider-add-field__hint provider-add-field__hint--error">{errors.baseUrl}</span>
        ) : (
          <span className="provider-add-field__hint">Must start with https://</span>
        )}
      </div>

      {/* API Key */}
      <div className="provider-add-field">
        <label className="provider-add-field__label">API Key</label>
        <input
          className={`provider-add-field__input${touched.apiKey && errors.apiKey ? " provider-add-field__input--error" : ""}`}
          type="password"
          value={apiKey}
          onChange={(e) => { setApiKey(e.target.value); setTouched((t) => ({ ...t, apiKey: true })); }}
          placeholder="sk-..."
        />
        {touched.apiKey && errors.apiKey ? (
          <span className="provider-add-field__hint provider-add-field__hint--error">{errors.apiKey}</span>
        ) : (
          <span className="provider-add-field__hint">At least 12 characters</span>
        )}
      </div>

      {/* API Format */}
      <div className="provider-add-field">
        <label className="provider-add-field__label">API Format</label>
        <select
          className="provider-add-field__select"
          value={apiFormat}
          onChange={(e) => setApiFormat(e.target.value)}
        >
          {API_FORMATS.map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>

      <div className="provider-add-form__actions">
        <button className="settings-form__save-btn" onClick={handleAdd} disabled={adding}>
          {adding ? "Adding..." : "Add"}
        </button>
        <button className="settings-form__cancel-btn" onClick={() => setShow(false)}>Cancel</button>
      </div>
    </div>
  );
}

/* ---- Generic Autocomplete ---- */

interface AcSuggestion {
  key: string;
  label: string;
  icon?: React.ReactNode;
  isSeparator?: boolean;
  isAction?: boolean;
}

function Autocomplete({
  suggestions,
  value,
  onChange,
  placeholder,
  hasError,
  errorHint,
  normalHint,
  onSelect,
}: {
  suggestions: AcSuggestion[];
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  hasError: boolean;
  errorHint: string | null;
  normalHint: string;
  onSelect?: (item: AcSuggestion) => void;
}) {
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const wrapRef = useRef<HTMLDivElement>(null);

  const filtered = suggestions.filter((s) =>
    s.label.toLowerCase().includes(value.toLowerCase())
  );

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const select = (item: AcSuggestion) => {
    if (item.isSeparator) return;
    if (item.isAction) {
      onChange("");
      onSelect?.(item);
    } else {
      onChange(item.label);
      onSelect?.(item);
    }
    setOpen(false);
    setHighlightIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
      setOpen(true);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((i) => {
        let next = i + 1;
        while (next < filtered.length && (filtered[next].isSeparator || filtered[next].isAction === undefined)) next++;
        return Math.min(next, filtered.length - 1);
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) => {
        let prev = i - 1;
        while (prev >= 0 && (filtered[prev].isSeparator || filtered[prev].isAction === undefined)) prev--;
        return Math.max(prev, -1);
      });
    } else if (e.key === "Enter" && highlightIndex >= 0) {
      e.preventDefault();
      select(filtered[highlightIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const highlightMatch = (text: string, query: string) => {
    if (!query) return <span>{text}</span>;
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return <span>{text}</span>;
    return (
      <span>
        {text.slice(0, idx)}
        <mark className="ac-match">{text.slice(idx, idx + query.length)}</mark>
        {text.slice(idx + query.length)}
      </span>
    );
  };

  return (
    <div className="ac" ref={wrapRef}>
      <div className="ac__input-wrap">
        {value && suggestions.some(s => s.label === value && s.icon) && (
          <span className="ac__input-icon">
            {suggestions.find(s => s.label === value)?.icon}
          </span>
        )}
        <input
          className={`ac__input${hasError ? " ac__input--error" : ""}${value && suggestions.some(s => s.label === value && s.icon) ? " ac__input--has-icon" : ""}`}
          type="text"
          value={value}
          onChange={(e) => { onChange(e.target.value); setOpen(true); setHighlightIndex(-1); }}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          autoComplete="off"
        />
      </div>
      {open && filtered.length > 0 && (
        <div className="ac__dropdown">
          {filtered.map((s, i) =>
            s.isSeparator ? (
              <div key={s.key} className="ac__separator" />
            ) : (
              <div
                key={s.key}
                className={`ac__item${i === highlightIndex ? " ac__item--highlight" : ""}${s.isAction ? " ac__item--action" : ""}`}
                onMouseDown={(e) => { e.preventDefault(); select(s); }}
                onMouseEnter={() => setHighlightIndex(i)}
              >
                {s.icon && <span className="ac__item-icon">{s.icon}</span>}
                <span className="ac__item-label">
                  {s.isAction ? s.label : highlightMatch(s.label, value)}
                </span>
              </div>
            )
          )}
        </div>
      )}
      {hasError && errorHint ? (
        <span className="provider-add-field__hint provider-add-field__hint--error">{errorHint}</span>
      ) : (
        <span className="provider-add-field__hint">{normalHint}</span>
      )}
    </div>
  );
}
