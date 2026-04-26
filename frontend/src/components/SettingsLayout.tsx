import { useUIStore } from "../stores/uiStore";
import SettingsNav from "./SettingsNav";
import ProviderList from "./ProviderList";
import ProviderDetail from "./ProviderDetail";

export default function SettingsLayout() {
  const settingsSubNav = useUIStore((s) => s.settingsSubNav);

  return (
    <div className="settings-layout">
      {/* Shared Header */}
      <div className="settings-layout__header">
        <h2 className="settings-layout__title">Settings</h2>
      </div>

      {/* Body: Col2 + Col3 + Col4 */}
      <div className="settings-layout__body">
        {/* Col2 — Settings Categories */}
        <div className="settings-layout__col2">
          <SettingsNav />
        </div>

        {/* Col3 — Provider List (or empty) */}
        <div className="settings-layout__col3">
          {settingsSubNav === "llm" ? <ProviderList /> : <Col3Empty />}
        </div>

        {/* Col4 — Provider Detail (or empty) */}
        <div className="settings-layout__col4">
          {settingsSubNav === "llm" ? <ProviderDetail /> : <Col4Empty />}
        </div>
      </div>
    </div>
  );
}

function Col3Empty() {
  return (
    <div className="settings-layout__empty">
      <p className="chatarea__empty-text">Select a settings category</p>
    </div>
  );
}

function Col4Empty() {
  return (
    <div className="settings-layout__empty">
      <p className="chatarea__empty-text">Select an item to view details</p>
    </div>
  );
}
