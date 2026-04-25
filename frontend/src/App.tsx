import SideNavBar from './components/SideNavBar';
import ProjectList from './components/ProjectList';
import ChatArea from './components/ChatArea';
import RightPanel from './components/RightPanel';
import { useUIStore } from './stores/uiStore';
import './App.css';

function App() {
  const col4Open = useUIStore((s) => s.col4Open);

  return (
    <div className="app-shell">
      <SideNavBar />
      <div className="app-main">
        <ProjectList />
        <ChatArea />
        {col4Open && <RightPanel />}
      </div>
    </div>
  );
}

export default App;
