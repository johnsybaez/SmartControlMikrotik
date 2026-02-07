import { Activity, Users, Zap, Server, Wifi, TrendingUp } from 'lucide-react';
import StatCard from './StatCard';
import { useEffect, useState } from 'react';
import api from '../services/api';

export default function DashboardHome() {
  const [stats, setStats] = useState([
    {
      title: 'Routers Activos',
      value: '0',
      icon: Server,
      color: 'bg-[#e00000]',
      trend: '+0%',
    },
    {
      title: 'Dispositivos Conectados',
      value: '0',
      icon: Wifi,
      color: 'bg-green-500',
      trend: '+0%',
    },
    {
      title: 'Internet Permitido',
      value: '0',
      icon: TrendingUp,
      color: 'bg-blue-500',
      trend: '0%',
    },
    {
      title: 'Internet Bloqueado',
      value: '0',
      icon: Activity,
      color: 'bg-orange-500',
      trend: '0%',
    },
  ]);

  const [recentActivity, setRecentActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
    const interval = setInterval(loadDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      const [statsResponse, activityResponse] = await Promise.all([
        api.get('/api/stats/summary'),
        api.get('/api/stats/recent-activity')
      ]);
      const statsData = statsResponse.data;
      setRecentActivity(activityResponse.data || []);
      
      // Update stats cards
      setStats([
        {
          title: 'Routers Activos',
          value: statsData.active_routers.toString(),
          icon: Server,
          color: 'bg-[#e00000]',
          trend: `${statsData.total_routers} total`,
        },
        {
          title: 'Dispositivos Totales',
          value: statsData.total_devices.toString(),
          icon: Wifi,
          color: 'bg-green-500',
          trend: `${statsData.total_assignments} con plan`,
        },
        {
          title: 'Internet Permitido',
          value: statsData.active_devices.toString(),
          icon: TrendingUp,
          color: 'bg-blue-500',
          trend: statsData.total_devices > 0 ? `${Math.round((statsData.active_devices / statsData.total_devices) * 100)}% del total` : '0%',
        },
        {
          title: 'Internet Bloqueado',
          value: statsData.blocked_devices.toString(),
          icon: Activity,
          color: 'bg-orange-500',
          trend: statsData.total_devices > 0 ? `${Math.round((statsData.blocked_devices / statsData.total_devices) * 100)}% del total` : '0%',
        },
      ]);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400">Resumen general del sistema SmartControl</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <StatCard key={stat.title} stat={stat} />
        ))}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Status */}
        <div className="bg-[#121212] border border-[#232323] rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="w-6 h-6 text-[#e00000]" />
            Estado del Sistema
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-[#232323]">
              <span className="text-gray-400">Backend API</span>
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-500 font-medium">Activo</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-[#232323]">
              <span className="text-gray-400">MikroTik Connection</span>
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-500 font-medium">Conectado</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-[#232323]">
              <span className="text-gray-400">Base de Datos</span>
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-green-500 font-medium">Operativa</span>
              </span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-gray-400">Última Sincronización</span>
              <span className="text-white font-medium">Hace 2 minutos</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-[#121212] border border-[#232323] rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Zap className="w-6 h-6 text-[#e00000]" />
            Actividad Reciente
          </h2>
          <div className="space-y-3">
            {loading ? (
              <p className="text-gray-400 text-center py-4">Cargando actividad...</p>
            ) : recentActivity.length > 0 ? (
              recentActivity.map((activity, index) => (
                <div key={index} className="py-2 border-b border-[#232323] last:border-0">
                  <p className="text-white text-sm">{activity.description}</p>
                  <p className="text-gray-500 text-xs mt-1">
                    {new Date(activity.timestamp).toLocaleString('es-DO', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
              ))
            ) : (
              <p className="text-gray-400 text-center py-4">No hay actividad reciente</p>
            )}
          </div>

          <div className="mt-6 pt-6 border-t border-[#232323]">
            <p className="text-gray-400 text-sm mb-2">Desarrollado por:</p>
            <p className="text-[#e00000] font-bold">BJ&C Baez Techno Solutions SRL</p>
          </div>
        </div>
      </div>
    </div>
  );
}
