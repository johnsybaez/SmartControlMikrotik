import { Activity, BarChart3, DollarSign, Server, Wifi } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../services/api';

export default function Statistics() {
  const [summary, setSummary] = useState(null);
  const [revenue, setRevenue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const [summaryResponse, revenueResponse] = await Promise.all([
        api.get('/api/stats/summary'),
        api.get('/api/stats/revenue')
      ]);
      setSummary(summaryResponse.data);
      setRevenue(revenueResponse.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Estadísticas</h1>
          <p className="text-gray-400 mt-1">Resumen y métricas operativas</p>
        </div>
        <button
          onClick={loadStats}
          className="bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded-lg"
        >
          Actualizar
        </button>
      </div>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/50 text-red-500 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-[#e00000]"></div>
          <p className="text-gray-400 mt-4">Cargando estadísticas...</p>
        </div>
      ) : (
        <>
          {summary && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <div className="bg-[#121212] border border-[#232323] rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Routers Activos</p>
                    <p className="text-2xl font-bold text-white">{summary.active_routers}</p>
                  </div>
                  <Server className="w-6 h-6 text-[#e00000]" />
                </div>
              </div>
              <div className="bg-[#121212] border border-[#232323] rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Dispositivos Totales</p>
                    <p className="text-2xl font-bold text-white">{summary.total_devices}</p>
                  </div>
                  <Wifi className="w-6 h-6 text-green-400" />
                </div>
              </div>
              <div className="bg-[#121212] border border-[#232323] rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Internet Permitido</p>
                    <p className="text-2xl font-bold text-white">{summary.active_devices}</p>
                  </div>
                  <Activity className="w-6 h-6 text-blue-400" />
                </div>
              </div>
              <div className="bg-[#121212] border border-[#232323] rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-400 text-sm">Planes Activos</p>
                    <p className="text-2xl font-bold text-white">{summary.active_plans}</p>
                  </div>
                  <BarChart3 className="w-6 h-6 text-orange-400" />
                </div>
              </div>
            </div>
          )}

          {revenue && (
            <div className="bg-[#121212] border border-[#232323] rounded-lg p-6">
              <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-[#e00000]" />
                Ingresos estimados
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div>
                  <p className="text-gray-400 text-sm">Ingreso mensual</p>
                  <p className="text-2xl font-bold text-white">${revenue.total_monthly_revenue.toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">Suscripciones</p>
                  <p className="text-2xl font-bold text-white">{revenue.total_subscriptions}</p>
                </div>
                <div>
                  <p className="text-gray-400 text-sm">ARPU</p>
                  <p className="text-2xl font-bold text-white">${revenue.average_revenue_per_user.toFixed(2)}</p>
                </div>
              </div>

              <div className="space-y-3">
                {revenue.plans.map((plan) => (
                  <div key={plan.plan_name} className="flex items-center justify-between border-b border-[#232323] pb-3">
                    <div>
                      <p className="text-white font-medium">{plan.plan_name}</p>
                      <p className="text-gray-500 text-sm">{plan.subscriptions} suscripciones</p>
                    </div>
                    <div className="text-right">
                      <p className="text-white font-semibold">${plan.revenue.toFixed(2)}</p>
                      <p className="text-gray-500 text-sm">${plan.price.toFixed(2)} c/u</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
