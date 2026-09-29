import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import Sidebar from "./components/Sidebar";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Inbox from "./pages/Inbox";
import EmailDetail from "./pages/EmailDetail";
import Bulk from "./pages/Bulk";
import Analytics from "./pages/Analytics";
import Accounts from "./pages/Accounts";

function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 min-w-0 px-8 py-6 pb-12">{children}</div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedLayout>
            <Dashboard />
          </ProtectedLayout>
        }
      />
      <Route
        path="/inbox"
        element={
          <ProtectedLayout>
            <Inbox />
          </ProtectedLayout>
        }
      />
      <Route
        path="/inbox/:id"
        element={
          <ProtectedLayout>
            <EmailDetail />
          </ProtectedLayout>
        }
      />
      <Route
        path="/bulk"
        element={
          <ProtectedLayout>
            <Bulk />
          </ProtectedLayout>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedLayout>
            <Analytics />
          </ProtectedLayout>
        }
      />
      <Route
        path="/accounts"
        element={
          <ProtectedLayout>
            <Accounts />
          </ProtectedLayout>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
