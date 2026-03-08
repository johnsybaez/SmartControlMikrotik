import './index.css';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useEffect, useRef } from 'react';
import useAuthStore from './store/authStore';
import Dashboard from './components/Dashboard';
import DashboardHome from './components/DashboardHome';
import ServicePlans from './pages/ServicePlans';
import Routers from './pages/Routers';
import Devices from './pages/Devices';
import Login from './pages/Login';
import Settings from './pages/Settings';
import UsersModule from './pages/UsersModule';

const IDLE_TIMEOUT_MINUTES = Number(import.meta.env.VITE_SESSION_IDLE_MINUTES || 30);

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
}

function IdleSessionGuard() {
  const { isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const idleTimerRef = useRef(null);

  useEffect(() => {
    if (!isAuthenticated) {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }
      return;
    }

    const timeoutMs = IDLE_TIMEOUT_MINUTES * 60 * 1000;

    const resetIdleTimer = () => {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }

      idleTimerRef.current = setTimeout(() => {
        logout();
        navigate('/login', { replace: true });
      }, timeoutMs);
    };

    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'];
    events.forEach((evt) => window.addEventListener(evt, resetIdleTimer, { passive: true }));
    resetIdleTimer();

    return () => {
      events.forEach((evt) => window.removeEventListener(evt, resetIdleTimer));
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }
    };
  }, [isAuthenticated, logout, navigate]);

  return null;
}

function App() {
  const { init } = useAuthStore();

  useEffect(() => {
    init();
  }, [init]);

  return (
    <BrowserRouter>
      <IdleSessionGuard />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardHome />} />
          <Route path="/routers" element={<Routers />} />
          <Route path="/devices" element={<Devices />} />
          <Route path="/plans" element={<ServicePlans />} />
          <Route path="/users" element={<UsersModule />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
