import './Dashboard.css';
import {
  Menu,
  Home,
  Settings,
  Users,
  Zap,
  Wifi,
  LogOut,
  Router,
  Sun,
  Moon,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, Outlet, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/authStore';

export default function Dashboard() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [theme, setTheme] = useState('dark');
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const isLight = theme === 'light';

  useEffect(() => {
    const savedTheme = localStorage.getItem('smartcontrol-theme');
    if (savedTheme === 'light' || savedTheme === 'dark') {
      setTheme(savedTheme);
    }
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleTheme = () => {
    const nextTheme = isLight ? 'dark' : 'light';
    setTheme(nextTheme);
    localStorage.setItem('smartcontrol-theme', nextTheme);
  };

  const menuItems = [
    { name: 'Dashboard', path: '/', icon: Home, roles: ['admin', 'operator'] },
    { name: 'Routers', path: '/routers', icon: Router, roles: ['admin'] },
    { name: 'Dispositivos', path: '/devices', icon: Wifi, roles: ['admin', 'operator'] },
    { name: 'Control de Ancho de Banda', path: '/plans', icon: Zap, roles: ['admin'] },
    { name: 'Usuarios', path: '/users', icon: Users, roles: ['admin'] },
    { name: 'Configuración', path: '/settings', icon: Settings, roles: ['admin'] },
  ];

  const visibleItems = menuItems.filter((item) => {
    if (!user?.role) return false;
    return item.roles.includes(user.role);
  });

  return (
    <div className={`flex h-screen ${isLight ? 'bg-white theme-light' : 'bg-gray-100'}`}>
      {/* Sidebar */}
      <aside
        className={`${
          isLight
            ? 'bg-white text-red-700 border-r border-red-200'
            : 'bg-gradient-to-b from-[#1a0505] via-[#0b0b0b] to-black text-white'
        } transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-20'} relative`}
      >
        <div className={`p-4 border-b ${isLight ? 'border-red-200' : 'border-[#232323]'}`}>
          <div className="flex items-center gap-3">
            <img src="/logo.svg" alt="BJ&C Logo" className="w-12 h-12 object-contain" />
            {sidebarOpen && (
              <div>
                <h1
                  className={`text-base font-bold ${isLight ? 'text-red-700' : 'text-[#e00000]'}`}
                >
                  BJ&C Baez
                </h1>
                <p className={`text-xs ${isLight ? 'text-red-400' : 'text-gray-400'}`}>
                  Techno Solutions
                </p>
              </div>
            )}
          </div>
        </div>

        <nav className="mt-6">
          {visibleItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 transition-colors border-l-4 border-transparent ${
                  isLight
                    ? 'hover:bg-red-50 hover:border-red-500'
                    : 'hover:bg-[#e00000] hover:bg-opacity-20 hover:border-[#e00000]'
                }`}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {sidebarOpen && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        <div className={`absolute bottom-0 left-0 right-0 p-4 border-t ${isLight ? 'border-red-200' : 'border-[#232323]'}`}>
          <button
            onClick={handleLogout}
            className={`flex items-center gap-3 w-full px-4 py-3 transition-colors rounded ${
              isLight ? 'hover:bg-red-50' : 'hover:bg-[#e00000] hover:bg-opacity-20'
            }`}
          >
            <LogOut className="w-5 h-5" />
            {sidebarOpen && <span>Cerrar Sesión</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className={`bg-white shadow ${isLight ? 'border-b border-red-200' : ''}`}>
          <div className="flex items-center justify-between px-6 py-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className={`p-2 rounded-lg ${isLight ? 'hover:bg-red-50' : 'hover:bg-gray-100'}`}
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className={`text-xl font-semibold ${isLight ? 'text-red-700' : 'text-gray-800'}`}>
              SmartControl Portal
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={toggleTheme}
                aria-pressed={isLight}
                className={`flex items-center gap-2 px-3 py-1.5 rounded border text-sm transition-colors ${
                  isLight
                    ? 'border-red-300 text-red-700 hover:bg-red-50'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-100'
                }`}
              >
                {isLight ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                <span>{isLight ? 'Modo claro' : 'Modo oscuro'}</span>
              </button>
              <div className={`text-sm ${isLight ? 'text-red-600' : 'text-gray-600'}`}>
                {user?.username || 'Usuario'} {user?.role && `(${user.role})`}
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className={`flex-1 overflow-auto ${isLight ? 'bg-white' : ''}`}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
