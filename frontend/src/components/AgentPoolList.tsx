import { useEffect, useState } from "react";
import { useAgentPoolStore } from "../stores/agentPoolStore";

export default function AgentPoolList() {
  const { templates, activeId, loading, fetchAll, setActive } = useAgentPoolStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAll().catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="projectlist">
      <div className="projectlist__header">
        <div className="projectlist__header-row">
          <h1 className="projectlist__title">Agents</h1>
        </div>
      </div>

      <div className="projectlist__list">
        {error && (
          <div className="projectlist__empty">
            <p style={{ color: "#e74c3c" }}>Failed to load agents</p>
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>{error}</p>
            <button className="projectlist__empty-btn" onClick={() => { setError(null); fetchAll().catch((e) => setError(String(e))); }}>
              Retry
            </button>
          </div>
        )}
        {!error && loading && templates.length === 0 && (
          <div className="projectlist__empty">Loading...</div>
        )}
        {!error && !loading && templates.length === 0 && (
          <div className="projectlist__empty">
            <p>No agent templates</p>
          </div>
        )}
        {!error && templates.map((t) => {
          const isActive = t.id === activeId;
          return (
            <div
              key={t.id}
              className={`projectlist__item${isActive ? " projectlist__item--active" : ""}`}
              onClick={() => setActive(t.id)}
            >
              <div
                className={`projectlist__item-avatar${isActive ? " projectlist__item-avatar--active" : ""}`}
              >
                {t.role === "lead" ? "L" : t.name.slice(0, 2).toUpperCase()}
              </div>
              <div className="projectlist__item-body">
                <div className="projectlist__item-row">
                  <span
                    className={`projectlist__item-name${isActive ? " projectlist__item-name--active" : ""}`}
                  >
                    {t.name}
                  </span>
                </div>
                <div className="projectlist__item-subrow">
                  <div className="projectlist__item-preview">
                    {t.role} {t.auto_join ? "· auto-join" : ""}
                  </div>
                </div>
              </div>
              {isActive && <div className="projectlist__item-accent" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
