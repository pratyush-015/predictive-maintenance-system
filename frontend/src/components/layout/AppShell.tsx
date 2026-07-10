import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { useDashboardData } from "../../store/dashboardData";

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/devices": "Devices",
  "/alerts": "Alerts",
  "/incidents": "Incident Timeline",
  "/models": "Model Comparison",
};

export function AppShell() {
  const { devices, selectedDeviceUid, setSelectedDeviceUid, wsStatus } = useDashboardData();
  const location = useLocation();
  const title = TITLES[location.pathname] ?? "Pulse";

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar
          title={title}
          devices={devices}
          selectedDeviceUid={selectedDeviceUid}
          onSelectDevice={setSelectedDeviceUid}
          wsStatus={wsStatus}
        />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
