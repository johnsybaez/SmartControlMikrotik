import { useState, useEffect } from 'react';
import { Router, Wifi, CheckCircle, XCircle, RefreshCw, Plus, Trash2 } from 'lucide-react';
import api from '../services/api';
import useAuthStore from '../store/authStore';
import Modal from '../components/Modal';

export default function Routers() {
  const [routers, setRouters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState({});
  const [deleting, setDeleting] = useState({});
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [form, setForm] = useState({
    name: '',
    host: '',
    api_port: 8728,
    ssh_port: 22,
    username: '',
    password: '',
    use_ssl: false,
    ssl_verify: false,
    timeout: 10,
    description: ''
  });
  const { user } = useAuthStore();

  useEffect(() => {
    loadRouters();
  }, []);

  const loadRouters = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/routers');
      setRouters(response.data);
    } catch (error) {
      console.error('Error loading routers:', error);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (routerId) => {
    setTesting(prev => ({ ...prev, [routerId]: true }));
    try {
      const response = await api.post(`/api/routers/${routerId}/test`);
      alert(`Conexión exitosa:\nVersión: ${response.data.version}\nBoard: ${response.data.board}\nMétodo: ${response.data.method}`);
    } catch (error) {
      alert(`Error de conexión: ${error.response?.data?.detail || error.message}`);
    } finally {
      setTesting(prev => ({ ...prev, [routerId]: false }));
    }
  };

  const openCreateModal = () => {
    setCreateError(null);
    setForm({
      name: '',
      host: '',
      api_port: 8728,
      ssh_port: 22,
      username: '',
      password: '',
      use_ssl: false,
      ssl_verify: false,
      timeout: 10,
      description: ''
    });
    setIsCreateOpen(true);
  };

  const handleCreateChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleCreateRouter = async () => {
    setCreateError(null);
    setCreateLoading(true);
    try {
      await api.post('/api/routers', {
        name: form.name,
        host: form.host,
        api_port: Number(form.api_port),
        ssh_port: Number(form.ssh_port),
        username: form.username,
        password: form.password,
        use_ssl: form.use_ssl,
        ssl_verify: form.ssl_verify,
        timeout: Number(form.timeout),
        description: form.description || null
      });
      setIsCreateOpen(false);
      await loadRouters();
    } catch (error) {
      setCreateError(error.response?.data?.detail || error.message);
    } finally {
      setCreateLoading(false);
    }
  };

  const deleteRouter = async (routerId, routerName) => {
    if (!confirm(`¿Estás seguro que deseas eliminar el router "${routerName}"?\n\nEsto eliminará también todos los dispositivos asociados a este router.`)) {
      return;
    }

    setDeleting(prev => ({ ...prev, [routerId]: true }));
    try {
      await api.delete(`/api/routers/${routerId}`);
      await loadRouters();
    } catch (error) {
      alert(`Error al eliminar router: ${error.response?.data?.detail || error.message}`);
    } finally {
      setDeleting(prev => ({ ...prev, [routerId]: false }));
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Routers MikroTik</h1>
          <p className="text-gray-500 mt-1">Gestión de routers y conexiones</p>
        </div>
        {user?.role === 'admin' && (
          <button
            onClick={openCreateModal}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Agregar Router
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {routers.map((router) => (
          <div key={router.id} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-blue-100 p-3 rounded-lg">
                  <Router className="w-6 h-6 text-blue-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-800">{router.name}</h3>
                  <p className="text-sm text-gray-500">{router.host}:{router.api_port}</p>
                </div>
              </div>
              {router.status === 'active' ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Puerto API:</span>
                <span className="font-medium">{router.api_port}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Puerto SSH:</span>
                <span className="font-medium">{router.ssh_port}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Usuario:</span>
                <span className="font-medium">{router.username}</span>
              </div>
              {router.location && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500">Ubicación:</span>
                  <span className="font-medium">{router.location}</span>
                </div>
              )}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => testConnection(router.id)}
                disabled={testing[router.id]}
                className="flex-1 bg-green-500 hover:bg-green-600 disabled:bg-gray-300 text-white px-3 py-2 rounded text-sm font-medium flex items-center justify-center gap-2"
              >
                {testing[router.id] ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Probando...
                  </>
                ) : (
                  <>
                    <Wifi className="w-4 h-4" />
                    Probar
                  </>
                )}
              </button>
              {user?.role === 'admin' && (
                <button 
                  onClick={() => deleteRouter(router.id, router.name)}
                  disabled={deleting[router.id]}
                  className="bg-red-500 hover:bg-red-600 disabled:bg-gray-300 text-white px-3 py-2 rounded text-sm"
                >
                  {deleting[router.id] ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {routers.length === 0 && (
        <div className="text-center py-12">
          <Router className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-600 mb-2">No hay routers configurados</h3>
          <p className="text-gray-500">Agrega tu primer router MikroTik para comenzar</p>
        </div>
      )}

      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Agregar Router"
      >
        <div className="space-y-4">
          {createError && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-500 px-4 py-3 rounded-lg text-sm">
              {createError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Nombre</label>
              <input
                value={form.name}
                onChange={(e) => handleCreateChange('name', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="Router Principal"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Host</label>
              <input
                value={form.host}
                onChange={(e) => handleCreateChange('host', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="10.80.0.1"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Puerto API</label>
                <input
                  type="number"
                  value={form.api_port}
                  onChange={(e) => handleCreateChange('api_port', e.target.value)}
                  className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Puerto SSH</label>
                <input
                  type="number"
                  value={form.ssh_port}
                  onChange={(e) => handleCreateChange('ssh_port', e.target.value)}
                  className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Usuario</label>
              <input
                value={form.username}
                onChange={(e) => handleCreateChange('username', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="admin"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Contraseña</label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => handleCreateChange('password', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="••••••••"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Descripción</label>
              <input
                value={form.description}
                onChange={(e) => handleCreateChange('description', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="Router principal"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Timeout (s)</label>
                <input
                  type="number"
                  value={form.timeout}
                  onChange={(e) => handleCreateChange('timeout', e.target.value)}
                  className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                />
              </div>
              <div className="flex items-center gap-3 mt-8">
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={form.use_ssl}
                    onChange={(e) => handleCreateChange('use_ssl', e.target.checked)}
                  />
                  Usar SSL
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={form.ssl_verify}
                    onChange={(e) => handleCreateChange('ssl_verify', e.target.checked)}
                  />
                  Verificar SSL
                </label>
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-[#232323]">
            <button
              onClick={() => setIsCreateOpen(false)}
              className="flex-1 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded-lg transition"
            >
              Cancelar
            </button>
            <button
              onClick={handleCreateRouter}
              disabled={createLoading || !form.name || !form.host || !form.username || !form.password}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {createLoading ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
