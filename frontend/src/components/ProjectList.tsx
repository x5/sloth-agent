import { useEffect, useState } from "react";
import { useInspirationStore } from "../stores/inspirationStore";
import { useUIStore } from "../stores/uiStore";

function formatTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) {
    return (words[0][0] + words[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export default function ProjectList() {
  const { inspirations, activeId, loading, fetchAll, create, remove, setActive } =
    useInspirationStore();
  const col2Collapsed = useUIStore((s) => s.col2Collapsed);
  const toggleCol2 = useUIStore((s) => s.toggleCol2);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSearch = (value: string) => {
    setSearch(value);
    fetchAll(value || undefined);
  };

  const handleCreate = () => {
    const name = prompt("Inspiration name:");
    if (name?.trim()) {
      create(name.trim());
    }
  };

  return (
    <div className={`projectlist${col2Collapsed ? " projectlist--collapsed" : ""}`}>
      {/* Header */}
      <div className="projectlist__header">
        <div className="projectlist__header-row">
          <h1 className="projectlist__title">Inspiration</h1>
          <button
            className="projectlist__add-btn"
            title="New Inspiration"
            onClick={handleCreate}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
          <div className="projectlist__collapsed-icon" title="Inspiration">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9ea7b0" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a7 7 0 0 0-7 7c0 2.4 1.2 4.5 3 5.7V18h8v-3.3c1.8-1.3 3-3.4 3-5.7a7 7 0 0 0-7-7z" />
              <line x1="9" y1="18" x2="15" y2="18" />
              <line x1="10" y1="21" x2="14" y2="21" />
            </svg>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="projectlist__search">
        <div className="projectlist__search-box">
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#4e6073"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            className="projectlist__search-input"
            type="text"
            placeholder="Search"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Project List */}
      <div className="projectlist__list">
        {loading && inspirations.length === 0 && (
          <div className="projectlist__empty">Loading...</div>
        )}
        {!loading && inspirations.length === 0 && (
          <div className="projectlist__empty">
            <p>No inspirations yet</p>
            <button className="projectlist__empty-btn" onClick={handleCreate}>
              Create your first inspiration
            </button>
          </div>
        )}
        {inspirations.map((p) => {
          const isActive = p.id === activeId;
          return (
            <div
              key={p.id}
              className={`projectlist__item${isActive ? " projectlist__item--active" : ""}`}
              onClick={() => setActive(p.id)}
            >
              <div
                className={`projectlist__item-avatar${isActive ? " projectlist__item-avatar--active" : ""}`}
              >
                {getInitials(p.name)}
              </div>
              <div className="projectlist__item-body">
                <div className="projectlist__item-row">
                  <span
                    className={`projectlist__item-name${isActive ? " projectlist__item-name--active" : ""}`}
                  >
                    {p.name}
                  </span>
                  <span className="projectlist__item-time">
                    {formatTime(p.latest_message_at || p.updated_at)}
                  </span>
                </div>
                <div className="projectlist__item-subrow">
                  <div className="projectlist__item-preview">
                    {p.agent_count === 1 ? "1 agent" : `${p.agent_count} agents`}
                  </div>
                  <button
                    className="projectlist__item-delete"
                    title="Delete inspiration"
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`Delete "${p.name}"?`)) {
                        remove(p.id);
                      }
                    }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
              </div>
              {isActive && <div className="projectlist__item-accent" />}
            </div>
          );
        })}
      </div>

      {/* Footer — collapse toggle */}
      <div className="projectlist__footer">
        <button
          className="projectlist__collapse-btn"
          title={col2Collapsed ? "Expand" : "Collapse"}
          onClick={toggleCol2}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {col2Collapsed ? (
              <polyline points="15 18 9 12 15 6" />
            ) : (
              <polyline points="9 18 15 12 9 6" />
            )}
          </svg>
        </button>
      </div>
    </div>
  );
}
