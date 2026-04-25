import AppLogo from "./AppLogo";

export default function SideNavBar() {
  return (
    <div className="sidenav">
      {/* Logo */}
      <div className="sidenav__logo">
        <AppLogo />
      </div>

      {/* Nav Icons */}
      <div className="sidenav__nav">
        <button className="sidenav__btn sidenav__btn--active" title="Inspiration">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a7 7 0 0 0-7 7c0 2.4 1.2 4.5 3 5.7V18h8v-3.3c1.8-1.3 3-3.4 3-5.7a7 7 0 0 0-7-7z" />
            <line x1="9" y1="18" x2="15" y2="18" />
            <line x1="10" y1="21" x2="14" y2="21" />
          </svg>
        </button>
        <button className="sidenav__btn" title="Agents">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="4" y="8" width="16" height="12" rx="3" />
            <circle cx="9" cy="14" r="1.5" />
            <circle cx="15" cy="14" r="1.5" />
            <line x1="9" y1="17" x2="15" y2="17" />
          </svg>
        </button>
        <button className="sidenav__btn" title="Settings">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="5" y1="21" x2="5" y2="17" />
            <line x1="5" y1="7" x2="5" y2="3" />
            <circle cx="5" cy="12" r="2" />
            <line x1="12" y1="21" x2="12" y2="14" />
            <line x1="12" y1="10" x2="12" y2="3" />
            <circle cx="12" cy="12" r="2" />
            <line x1="19" y1="21" x2="19" y2="19" />
            <line x1="19" y1="5" x2="19" y2="3" />
            <circle cx="19" cy="12" r="2" />
          </svg>
        </button>
      </div>

      {/* Spacer */}
      <div className="sidenav__spacer" />

      {/* User Avatar */}
      <div className="sidenav__profile">
        <div className="sidenav__avatar">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4e6073" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </div>
      </div>
    </div>
  );
}
