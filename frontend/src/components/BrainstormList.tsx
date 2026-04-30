import { useEffect, useRef, useState } from "react";
import { useBrainstormStore } from "../stores/brainstormStore";
import { useInspirationStore } from "../stores/inspirationStore";

function formatTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  if (isToday) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  }
  return (
    date.toLocaleDateString([], { month: "short", day: "numeric" }) +
    " " +
    date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
  );
}

export default function BrainstormList() {
  const activeInspirationId = useInspirationStore((s) => s.activeId);
  const activeInspiration = useInspirationStore((s) =>
    s.inspirations.find((i) => i.id === s.activeId)
  );

  const sessions = useBrainstormStore((s) => s.sessions);
  const activeId = useBrainstormStore((s) => s.activeId);
  const loading = useBrainstormStore((s) => s.loading);
  const fetchAll = useBrainstormStore((s) => s.fetchAll);
  const create = useBrainstormStore((s) => s.create);
  const setActive = useBrainstormStore((s) => s.setActive);

  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (activeInspirationId) {
      fetchAll(activeInspirationId);
    }
  }, [activeInspirationId]);

  useEffect(() => {
    if (creating && inputRef.current) {
      inputRef.current.focus();
    }
  }, [creating]);

  const handleCreate = async () => {
    const title = newTitle.trim();
    if (!title || !activeInspirationId || submitting) return;
    setSubmitting(true);
    try {
      await create(activeInspirationId, title);
      setNewTitle("");
      setCreating(false);
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleCreate();
    } else if (e.key === "Escape") {
      setCreating(false);
      setNewTitle("");
    }
  };

  return (
    <div className="projectlist">
      <div className="projectlist__header">
        <h2 className="projectlist__title">Brainstorm</h2>
        <button
          className="projectlist__add-btn"
          title="New Brainstorm Session"
          onClick={() => setCreating(true)}
          disabled={!activeInspirationId}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </button>
      </div>

      {!activeInspirationId ? (
        <div className="projectlist__empty">
          <p className="projectlist__empty-text">Select an inspiration first</p>
        </div>
      ) : (
        <>
          {creating && (
            <div className="projectlist__inline-create">
              <input
                ref={inputRef}
                className="projectlist__inline-input"
                type="text"
                placeholder="Session title..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={submitting}
              />
              <div className="projectlist__inline-actions">
                <button className="projectlist__inline-cancel" onClick={() => { setCreating(false); setNewTitle(""); }}>Cancel</button>
                <button className="projectlist__inline-create-btn" onClick={handleCreate} disabled={!newTitle.trim() || submitting}>
                  {submitting ? "Creating..." : "Create"}
                </button>
              </div>
            </div>
          )}

          {loading ? (
            <div className="projectlist__loading" />
          ) : sessions.length === 0 ? (
            <div className="projectlist__empty">
              <p className="projectlist__empty-text">
                {activeInspiration
                  ? `No brainstorm sessions in "${activeInspiration.name}"`
                  : "No sessions yet"}
              </p>
            </div>
          ) : (
            <div className="projectlist__list">
              {sessions.map((s) => (
                <button
                  key={s.id}
                  className={`projectlist__item${s.id === activeId ? " projectlist__item--active" : ""}`}
                  onClick={() => setActive(s.id)}
                >
                  <span className="projectlist__item-name">{s.title}</span>
                  <span className="projectlist__item-meta">
                    <span className={`projectlist__status projectlist__status--${s.status}`}>{s.status}</span>
                    <span className="projectlist__item-time">{formatTime(s.created_at)}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
