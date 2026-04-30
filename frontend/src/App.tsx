import SideNavBar from './components/SideNavBar';
import ProjectList from './components/ProjectList';
import ChatArea from './components/ChatArea';
import RightPanel from './components/RightPanel';
import AgentPoolList from './components/AgentPoolList';
import AgentDetail from './components/AgentDetail';
import SettingsLayout from './components/SettingsLayout';
import { useUIStore } from './stores/uiStore';
import './App.css';

function App() {
  const activeNav = useUIStore((s) => s.activeNav);
  const col4Open = useUIStore((s) => s.col4Open);

  // Settings uses its own shared-header layout
  if (activeNav === "settings") {
    return (
      <div className="app-shell">
        <SideNavBar />
        <SettingsLayout />
      </div>
    );
  }

  const col2 = activeNav === "agents"
    ? <AgentPoolList />
    : <ProjectList />;

  const col3 = activeNav === "agents"
    ? <AgentDetail />
    : <ChatArea />;

  return (
    <div className="app-shell">
      <SideNavBar />
      <div className="app-main">
        {col2}
        {col3}
        {col4Open && <RightPanel />}
      </div>
    </div>
  );
}

export default App;
