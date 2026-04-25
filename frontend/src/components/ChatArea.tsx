import { useInspirationStore } from "../stores/inspirationStore";
import { useUIStore } from "../stores/uiStore";

export default function ChatArea() {
  const inspirations = useInspirationStore((s) => s.inspirations);
  const activeId = useInspirationStore((s) => s.activeId);
  const activeInspiration = inspirations.find((i) => i.id === activeId);

  const col4Content = useUIStore((s) => s.col4Content);
  const openCol4 = useUIStore((s) => s.openCol4);

  return (
    <div className="chatarea">
      {/* TopAppBar */}
      <div className="chatarea__topbar">
        <div className="chatarea__topbar-left">
          {activeInspiration ? (
            <>
              <h2 className="chatarea__project-name">{activeInspiration.name}</h2>
              <span className="chatarea__tag">MVP</span>
              <span className="chatarea__status">
                <span className="chatarea__status-dot" />
                1 ACTIVE
              </span>
            </>
          ) : (
            <h2 className="chatarea__project-name chatarea__project-name--dimmed">
              Sloth Agent
            </h2>
          )}
        </div>
        <div className="chatarea__topbar-actions">
          <button className={`chatarea__icon-btn${col4Content === "team" ? " chatarea__icon-btn--active" : ""}`} title="Team" onClick={() => openCol4("team")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="9" cy="8" r="4" />
              <path d="M1 20v-2a4 4 0 0 1 4-4h8a4 4 0 0 1 4 4v2" />
              <circle cx="18" cy="8" r="3" />
              <path d="M22 20v-2a3 3 0 0 0-2-2.8" />
            </svg>
          </button>
          <button className={`chatarea__icon-btn${col4Content === "status" ? " chatarea__icon-btn--active" : ""}`} title="Status" onClick={() => openCol4("status")}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </button>
          <button className="chatarea__icon-btn" title="More Options">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="12" cy="5" r="2" /><circle cx="12" cy="12" r="2" /><circle cx="12" cy="19" r="2" />
            </svg>
          </button>
        </div>
      </div>

      {/* Chat Canvas */}
      <div className="chatarea__canvas">
        <div className="chatarea__empty">
          <div className="chatarea__empty-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#c7c7c7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
            </svg>
          </div>
          <p className="chatarea__empty-text">
            {activeInspiration
              ? `Start chatting in "${activeInspiration.name}"`
              : "Select an inspiration to start chatting"}
          </p>
        </div>
      </div>

      {/* Input Area */}
      <div className="chatarea__input">
        <div className="chatarea__input-box">
          <div className="chatarea__input-field" contentEditable={false}>
            <span className="chatarea__input-placeholder">
              {activeInspiration
                ? "Chat coming in the next update..."
                : "Select an inspiration to start..."}
            </span>
          </div>
          <div className="chatarea__input-actions">
            <div className="chatarea__input-tools">
              <button className="chatarea__tool-btn" title="Attach File" disabled>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#c7c7c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <button className="chatarea__tool-btn" title="Mention Agent" disabled>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#c7c7c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
              </button>
            </div>
            <button className="chatarea__send-btn" disabled>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
