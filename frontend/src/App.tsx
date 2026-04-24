import SideNavBar from './components/SideNavBar';
import ProjectList from './components/ProjectList';
import ChatArea from './components/ChatArea';
import RightPanel from './components/RightPanel';
import './App.css';

function App() {
  return (
    <div className="app-shell">
      <SideNavBar />
      <div className="app-main">
        <ProjectList />
        <ChatArea />
        <RightPanel />
      </div>
    </div>
  );
}

export default App;
