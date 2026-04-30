import { useBrainstormStore } from "../stores/brainstormStore";

function formatTime(iso: string): string {
  const date = new Date(iso);
  return (
    date.toLocaleDateString([], { month: "short", day: "numeric" }) +
    " " +
    date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
  );
}

export default function BrainstormSessionDetail() {
  const sessions = useBrainstormStore((s) => s.sessions);
  const activeId = useBrainstormStore((s) => s.activeId);
  const session = sessions.find((s) => s.id === activeId);

  if (!session) {
    return (
      <div className="chatarea">
        <div className="chatarea__empty">
          <div className="chatarea__empty-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c7c7c7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a3 3 0 0 0-3-3" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <p className="chatarea__empty-text">Select a brainstorm session</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chatarea">
      <div className="chatarea__topbar">
        <div className="chatarea__topbar-left">
          <h2 className="chatarea__project-name">{session.title}</h2>
          <span className="chatarea__status">
            <span className={`chatarea__status-dot chatarea__status-dot--${session.status === "active" ? "working" : "idle"}`} />
            {session.status}
          </span>
        </div>
      </div>

      <div className="chatarea__canvas">
        <div className="brainstorm-detail">
          <div className="brainstorm-detail__section">
            <h3 className="brainstorm-detail__label">Sandbox</h3>
            <code className="brainstorm-detail__path">{session.sandbox_path}</code>
          </div>

          <div className="brainstorm-detail__section">
            <h3 className="brainstorm-detail__label">Settings</h3>
            <div className="brainstorm-detail__grid">
              <div className="brainstorm-detail__field">
                <span className="brainstorm-detail__key">Max Messages</span>
                <span className="brainstorm-detail__value">{session.max_messages}</span>
              </div>
              <div className="brainstorm-detail__field">
                <span className="brainstorm-detail__key">Cooldown</span>
                <span className="brainstorm-detail__value">{session.cooldown_seconds}s</span>
              </div>
              <div className="brainstorm-detail__field">
                <span className="brainstorm-detail__key">Message Count</span>
                <span className="brainstorm-detail__value">{session.message_count}</span>
              </div>
              <div className="brainstorm-detail__field">
                <span className="brainstorm-detail__key">Created</span>
                <span className="brainstorm-detail__value">{formatTime(session.created_at)}</span>
              </div>
            </div>
          </div>

          {session.file_tree.length > 0 && (
            <div className="brainstorm-detail__section">
              <h3 className="brainstorm-detail__label">Files ({session.file_tree.length})</h3>
              <ul className="brainstorm-detail__file-list">
                {session.file_tree.map((f) => (
                  <li key={f.path} className={`brainstorm-detail__file brainstorm-detail__file--${f.type}`}>
                    <span className="brainstorm-detail__file-icon">{f.type === "directory" ? "📁" : "📄"}</span>
                    <span className="brainstorm-detail__file-name">{f.name}</span>
                    <span className="brainstorm-detail__file-path">{f.path}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {session.file_tree.length === 0 && (
            <div className="brainstorm-detail__section">
              <h3 className="brainstorm-detail__label">Files</h3>
              <p className="brainstorm-detail__empty-files">No files generated yet. Start a discussion in Iter-5.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
