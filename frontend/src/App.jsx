import './index.css';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import useAuthStore from './store/authStore';
import Dashboard from './components/Dashboard';
import DashboardHome from './components/DashboardHome';
import ServicePlans from './pages/ServicePlans';
import Routers from './pages/Routers';
import Devices from './pages/Devices';
import Login from './pages/Login';
import Settings from './pages/Settings';
import UsersModule from './pages/UsersModule';

// Protected Route wrapper
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

function App() {
  const { init } = useAuthStore();

  useEffect(() => {
    init();
  }, [init]);

  return (
    <BrowserRouter>
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
