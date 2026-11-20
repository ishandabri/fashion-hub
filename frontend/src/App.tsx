import * as React from "react";
import { FormEvent, Suspense, lazy, useEffect, useState } from "react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  AlertCircle,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  Package,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Toaster, toast } from "sonner";
import { api } from "./lib/api";
import { BusyButton, ConfirmDialog, Page, SkeletonBlock } from "./components/app-ui";
const DashboardPage = lazy(() => import("./features/dashboard").then(({ DashboardPage }) => ({ default: DashboardPage })));
const EntriesPage = lazy(() => import("./features/entries").then(({ Entries }) => ({ default: Entries })));
const InventoryPage = lazy(() => import("./features/inventory").then(({ InventoryPage }) => ({ default: InventoryPage })));

type User = { username: string; must_change_password: boolean };
type AuthConfig = { username: string };
function useConnection() {
  const [online, setOnline] = useState(() => navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    const failed = () => setOnline(false);
    const recovered = () => setOnline(true);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    window.addEventListener("app:offline", failed);
    window.addEventListener("app:online", recovered);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
      window.removeEventListener("app:offline", failed);
      window.removeEventListener("app:online", recovered);
    };
  }, []);
  return online;
}
function ConnectionStatus({ online }: { online: boolean }) {
  return (
    <div
      className={`connection ${online ? "connected" : "disconnected"}`}
      role="status"
      aria-live="polite"
      aria-label={online ? "Online" : "Offline — writes disabled"}
      title={online ? "Online" : "Offline — writes disabled"}
    >
      {online ? (
        <Wifi size={14} aria-hidden="true" />
      ) : (
        <WifiOff size={14} aria-hidden="true" />
      )}
      <span>{online ? "Online" : "Offline — writes disabled"}</span>
    </div>
  );
}
function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { data: config } = useQuery({
    queryKey: ["auth-config"],
    queryFn: () => api<AuthConfig>("/api/v1/auth/config"),
  });
  useEffect(() => {
    if (config?.username && !username) setUsername(config.username);
  }, [config, username]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api<User>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      toast.success("Signed in");
      navigate("/dashboard");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <main className="auth-page">
      <form className="card auth-card" onSubmit={submit}>
        <p className="eyebrow">Store Manager</p>
        <h1>Sign in</h1>
        <p className="muted">Manage sales, inventory, and store performance.</p>
        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && (
          <p className="error" role="alert">
            <AlertCircle size={16} />
            {error}
          </p>
        )}
        <BusyButton className="primary" type="submit" busy={busy}>
          Sign in
        </BusyButton>
      </form>
    </main>
  );
}

function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const queryClient = useQueryClient();
  const online = useConnection();
  const [confirm, setConfirm] = useState(false);
  const logout = async () => {
    try {
      await api<void>("/api/v1/auth/logout", { method: "POST" });
      queryClient.clear();
      window.location.href = "/";
    } catch (e) {
      toast.error((e as Error).message);
    }
  };
  const links = [
    ["Dashboard", "/dashboard", LayoutDashboard],
    ["Entries", "/entries", ClipboardList],
    ["Inventory", "/inventory", Package],
  ] as const;
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Store Manager</p>
          <strong>Fashion Hub</strong>
        </div>
        <div className="topbar-actions">
          <ConnectionStatus online={online} />
          <button className="ghost signout-button" aria-label="Sign out" title="Sign out" onClick={() => setConfirm(true)}>
            <LogOut size={16} />
            <span className="signout-label">Sign out</span>
          </button>
        </div>
      </header>
      {!online && (
        <div className="offline-banner" role="alert">
          <WifiOff size={16} />
          You are offline. Financial writes are disabled until the connection
          returns.
        </div>
      )}
      <main className="page">{children}</main>
      <nav className="bottom-nav" aria-label="Primary navigation">
        {links.map(([label, href, Icon]) => (
          <Link
            className={location.pathname.startsWith(href) ? "active" : ""}
            to={href}
            key={href}
          >
            <Icon size={18} aria-hidden="true" />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
      {confirm && (
        <ConfirmDialog
          title="Sign out?"
          description="You can sign back in on this or another device."
          confirmLabel="Sign out"
          onConfirm={logout}
          onClose={() => setConfirm(false)}
        />
      )}
    </div>
  );
}

function Protected() {
  const { data, isLoading } = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/api/v1/auth/me"),
    retry: false,
  });
  const online = useConnection();
  const queryClient = useQueryClient();
  useEffect(() => {
    const reconnect = () => queryClient.refetchQueries({ type: "active" });
    window.addEventListener("online", reconnect);
    return () => window.removeEventListener("online", reconnect);
  }, [queryClient]);
  if (isLoading) return <SkeletonBlock />;
  if (!data) return <Navigate to="/" replace />;
  return (
    <Layout>
      <Routes>
        <Route
          path="/dashboard"
          element={<Suspense fallback={<SkeletonBlock />}><DashboardPage /></Suspense>}
        />
        <Route path="/entries" element={<Suspense fallback={<SkeletonBlock />}><EntriesPage online={online} /></Suspense>} />
        <Route
          path="/inventory"
          element={
            <Suspense fallback={<SkeletonBlock />}><Page title="Inventory"><InventoryPage online={online} /></Page></Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
}
export function App() {
  return (
    <>
      <Toaster position="top-center" richColors />
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/*" element={<Protected />} />
      </Routes>
    </>
  );
}
