import { useEffect } from "react";
import { useLLMStore } from "../stores/llmStore";
import { useUIStore } from "../stores/uiStore";

export default function SettingsNav() {
  const configs = useLLMStore((s) => s.configs);
  const fetchAll = useLLMStore((s) => s.fetchAll);
  const settingsSubNav = useUIStore((s) => s.settingsSubNav);
  const setSettingsSubNav = useUIStore((s) => s.setSettingsSubNav);

  useEffect(() => {
    fetchAll();
  }, []);

  return (
    <div className="settings-nav">
      <div className="settings-nav__list">
        {/* LLM Provider */}
        <div
          className={`projectlist__item${settingsSubNav === "llm" ? " projectlist__item--active" : ""}`}
          onClick={() => setSettingsSubNav("llm")}
        >
          <div
            className={`projectlist__item-avatar${settingsSubNav === "llm" ? " projectlist__item-avatar--active" : ""}`}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="4" y="4" width="16" height="16" rx="2" />
              <line x1="9" y1="2" x2="9" y2="4" />
              <line x1="15" y1="2" x2="15" y2="4" />
              <line x1="9" y1="20" x2="9" y2="22" />
              <line x1="15" y1="20" x2="15" y2="22" />
              <line x1="2" y1="9" x2="4" y2="9" />
              <line x1="2" y1="15" x2="4" y2="15" />
              <line x1="20" y1="9" x2="22" y2="9" />
              <line x1="20" y1="15" x2="22" y2="15" />
            </svg>
          </div>
          <div className="projectlist__item-body">
            <div className="projectlist__item-row">
              <span
                className={`projectlist__item-name${settingsSubNav === "llm" ? " projectlist__item-name--active" : ""}`}
              >
                LLM Provider
              </span>
            </div>
            <div className="projectlist__item-subrow">
              <div className="projectlist__item-preview">
                {configs.length > 0
                  ? `${configs.length} configured`
                  : "Not configured"}
              </div>
            </div>
          </div>
          {settingsSubNav === "llm" && <div className="projectlist__item-accent" />}
        </div>
      </div>
    </div>
  );
}
