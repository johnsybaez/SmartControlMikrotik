import { Shield, Sliders, User } from 'lucide-react';
import { useEffect, useState } from 'react';
import api from '../services/api';
import useAuthStore from '../store/authStore';

export default function Settings() {
  const { user } = useAuthStore();
  const [error, setError] = useState(null);
  const [audit, setAudit] = useState([]);

  useEffect(() => {
    if (user?.role === 'admin') {
      loadAudit();
    }
  }, [user?.role]);

  const loadAudit = async () => {
    try {
      const response = await api.get('/api/audit?limit=50');
      setAudit(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };


  if (user?.role !== 'admin') {
    return (
      <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
        <h1 className="text-2xl font-bold text-white">Configuración</h1>
        <p className="text-gray-400 mt-2">No tienes permisos para acceder a este módulo.</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Configuración</h1>
        <p className="text-gray-400 mt-1">Preferencias del sistema y cuenta</p>
      </div>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/50 text-red-500 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-[#121212] border border-[#232323] rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <Sliders className="w-5 h-5 text-[#e00000]" />
            Parámetros generales
          </h2>
          <p className="text-gray-400 text-sm">
            Este módulo está listo para conectar ajustes globales del portal.
          </p>
        </div>

        <div className="bg-[#121212] border border-[#232323] rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <User className="w-5 h-5 text-[#e00000]" />
            Perfil
          </h2>
          <p className="text-gray-400 text-sm">
            Aquí podrás editar datos del usuario autenticado.
          </p>
        </div>

        <div className="bg-[#121212] border border-[#232323] rounded-lg p-6">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-[#e00000]" />
            Seguridad
          </h2>
          <p className="text-gray-400 text-sm">
            Pendiente de configuración de políticas y credenciales.
          </p>
        </div>

        <div className="bg-[#121212] border border-[#232323] rounded-lg p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold text-white mb-4">Trazabilidad (últimos eventos)</h2>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {audit.map((event) => (
              <div key={event.id} className="border-b border-[#232323] pb-2">
                <p className="text-white text-sm">{event.action}</p>
                <p className="text-gray-500 text-xs">
                  {event.username || 'sistema'} • {new Date(event.timestamp).toLocaleString('es-DO')}
                </p>
              </div>
            ))}
            {audit.length === 0 && (
              <p className="text-gray-400 text-sm">No hay eventos registrados.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
