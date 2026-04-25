import { useUIStore } from "../stores/uiStore";

export default function RightPanel() {
  const col4Content = useUIStore((s) => s.col4Content);
  const closeCol4 = useUIStore((s) => s.closeCol4);

  return (
    <div className="rightpanel">
      <div className="rightpanel__header">
        <span className="rightpanel__title">
          {col4Content === "team" ? "Team" : "Status"}
        </span>
        <button className="rightpanel__close-btn" onClick={closeCol4} title="Close">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
      <div className="rightpanel__body">
        {col4Content === "team" ? (
          <div className="rightpanel__content">
            <h3 className="rightpanel__section-title">Team Members</h3>
            <p className="rightpanel__placeholder">Agent team configuration — coming in a future update</p>
          </div>
        ) : (
          <div className="rightpanel__content">
            <h3 className="rightpanel__section-title">Activity</h3>
            <p className="rightpanel__placeholder">Status feed and logs — coming in a future update</p>
          </div>
        )}
      </div>
    </div>
  );
}
