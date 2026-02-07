import { useState, useEffect } from 'react';
import { Smartphone, Shield, ShieldOff, RefreshCw, Search, Filter, LayoutGrid, List, Wifi, Download } from 'lucide-react';
import api from '../services/api';
import Modal from '../components/Modal';

export default function Devices() {
  const [devices, setDevices] = useState([]);
  const [routers, setRouters] = useState([]);
  const [selectedRouter, setSelectedRouter] = useState('');
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all'); // all, permitted, blocked, unknown
  const [viewMode, setViewMode] = useState('cards'); // 'cards' or 'list'
  const [syncing, setSyncing] = useState(false);
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [pendingDevice, setPendingDevice] = useState(null);
  const [planActionLoading, setPlanActionLoading] = useState(false);
  const [planActionError, setPlanActionError] = useState(null);

  useEffect(() => {
    loadRouters();
  }, []);

  useEffect(() => {
    if (selectedRouter) {
      loadDevices();
    }
  }, [selectedRouter]);

  const loadRouters = async () => {
    try {
      const response = await api.get('/api/routers');
      setRouters(response.data);
      if (response.data.length > 0) {
        setSelectedRouter(response.data[0].id.toString());
      }
    } catch (error) {
      console.error('Error loading routers:', error);
    }
  };

  const loadDevices = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/api/devices?router_id=${selectedRouter}`);
      setDevices(response.data);
    } catch (error) {
      console.error('Error loading devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const syncDHCPLeases = async () => {
    try {
      setSyncing(true);
      const response = await api.post(`/api/routers/${selectedRouter}/sync-dhcp-leases`);
      alert(`Sincronización completa: ${response.data.devices_created} creados, ${response.data.devices_updated} actualizados`);
      await loadDevices();
    } catch (error) {
      alert(`Error sincronizando: ${error.response?.data?.detail || error.message}`);
    } finally {
      setSyncing(false);
    }
  };

  const toggleDeviceInternet = async (device) => {
    if (!device.ip) {
      alert('El dispositivo no tiene dirección IP asignada');
      return;
    }

    const currentlyAllowed = device.internet_status === 'permitted' || device.internet_status === 'limited';
    const action = currentlyAllowed ? 'bloquear' : 'permitir';
    
    if (!confirm(`¿Desea ${action} el acceso a internet para ${device.hostname || device.ip}?`)) {
      return;
    }

    try {
      if (!currentlyAllowed) {
        // Mostrar modal para seleccionar tipo de plan
        setPendingDevice(device);
        setPlanActionError(null);
        setPlanModalOpen(true);
        return;
      }

      // Bloquear: eliminar de permitidos/limitados y agregar a bloqueados
      await api.post(
        `/api/routers/${selectedRouter}/toggle-internet`,
        {
          ip_address: device.ip,
          enable: false,
          comment: `SmartControl Portal - Bloqueado - ${device.hostname || 'Dispositivo'}`
        },
        { timeout: 30000 }
      );

      // Actualizar lista de dispositivos
      await loadDevices();
    } catch (error) {
      alert(`Error al ${action}: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleAllowDevice = async (listType) => {
    if (!pendingDevice) return;
    setPlanActionError(null);
    setPlanActionLoading(true);
    try {
      await api.post(
        `/api/routers/${selectedRouter}/toggle-internet`,
        {
          ip_address: pendingDevice.ip,
          enable: true,
          list_type: listType,
          comment: `SmartBJ Portal - ${pendingDevice.hostname || 'Dispositivo'}`
        },
        { timeout: 30000 }
      );
      setPlanModalOpen(false);
      setPendingDevice(null);
      await loadDevices();
    } catch (error) {
      setPlanActionError(error.response?.data?.detail || error.message);
    }
    setPlanActionLoading(false);
  };

  const filteredDevices = devices.filter(device => {
    const matchesSearch =
      (device.hostname?.toLowerCase() || '').includes(searchTerm.toLowerCase()) ||
      (device.ip || '').includes(searchTerm) ||
      (device.mac || '').toLowerCase().includes(searchTerm.toLowerCase());

    const status = device.internet_status || 'unknown';
    const isPermitted = status === 'permitted' || status === 'limited';
    const isBlocked = status === 'blocked';
    const isPending = !isPermitted && !isBlocked;
    const isBound = device.state === 'bound';

    let matchesFilter = false;
    if (filter === 'all') {
      matchesFilter = isPermitted || isBlocked || (isPending && isBound);
    } else if (filter === 'unknown') {
      matchesFilter = isPending && isBound;
    } else if (filter === 'permitted') {
      matchesFilter = status === 'permitted' || status === 'limited';
    } else {
      matchesFilter = status === filter;
    }

    return matchesSearch && matchesFilter;
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'permitted':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/50">
            <Shield className="w-3 h-3 inline mr-1" />
            Permitido
          </span>
        );
      case 'limited':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/50">
            <Shield className="w-3 h-3 inline mr-1" />
            Limitado
          </span>
        );
      case 'blocked':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/50">
            <ShieldOff className="w-3 h-3 inline mr-1" />
            Bloqueado
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400 border border-yellow-500/50">
            <Wifi className="w-3 h-3 inline mr-1 text-yellow-400" />
            Pendiente
          </span>
        );
    }
  };

  return (
    <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Dispositivos</h1>
          <p className="text-gray-400">Gestión de acceso a internet - BJ&C</p>
        </div>
        <div className="flex gap-3">
          <div className="bg-[#121212] border border-[#232323] rounded-lg p-1 flex">
            <button
              onClick={() => setViewMode('cards')}
              className={`px-3 py-2 rounded flex items-center gap-2 transition ${
                viewMode === 'cards'
                  ? 'bg-[#e00000] text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <LayoutGrid className="w-4 h-4" />
              Tarjetas
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-2 rounded flex items-center gap-2 transition ${
                viewMode === 'list'
                  ? 'bg-[#e00000] text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <List className="w-4 h-4" />
              Lista
            </button>
          </div>
        </div>
      </div>

      <div className="bg-[#121212] border border-[#232323] rounded-lg shadow-lg p-4 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Router</label>
            <select
              value={selectedRouter}
              onChange={(e) => setSelectedRouter(e.target.value)}
              className="w-full bg-[#1a1a1a] border border-[#232323] text-white rounded-lg px-3 py-2"
            >
              {routers.map(router => (
                <option key={router.id} value={router.id}>{router.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Buscar</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="IP, MAC o nombre..."
                className="w-full pl-10 pr-4 py-2 bg-[#1a1a1a] border border-[#232323] text-white rounded-lg placeholder-gray-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">Filtro</label>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="w-full bg-[#1a1a1a] border border-[#232323] text-white rounded-lg px-3 py-2"
            >
              <option value="all">Todos</option>
              <option value="permitted">Permitidos</option>
              <option value="blocked">Bloqueados</option>
              <option value="unknown">Sin estado</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={syncDHCPLeases}
              disabled={syncing || !selectedRouter}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2"
            >
              <Download className={`w-4 h-4 ${syncing ? 'animate-bounce' : ''}`} />
              {syncing ? 'Sincronizando...' : 'Sincronizar'}
            </button>
          </div>

          <div className="flex items-end">
            <button
              onClick={loadDevices}
              disabled={loading}
              className="w-full bg-gradient-to-r from-[#e00000] to-[#b80000] hover:from-[#ff0000] hover:to-[#e00000] text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 shadow-lg shadow-[#e00000]/30"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Actualizar
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#e00000]"></div>
        </div>
      ) : (
        <>
          <div className="mb-4 text-gray-400 text-sm">
            Mostrando {filteredDevices.length} de {devices.length} dispositivos
          </div>

          {viewMode === 'cards' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredDevices.map((device, index) => (
                <div
                  key={index}
                  className="bg-[#121212] border border-[#232323] rounded-lg p-4 hover:border-[#e00000]/50 transition"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <Smartphone className="w-5 h-5 text-[#e00000]" />
                      <h3 className="font-semibold text-white truncate">
                        {device.hostname || 'Sin nombre'}
                      </h3>
                    </div>
                    {getStatusBadge(device.internet_status)}
                  </div>

                  <div className="space-y-2 text-sm mb-4">
                    <div className="flex justify-between">
                      <span className="text-gray-400">IP:</span>
                      <span className="text-white font-mono">{device.ip || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">MAC:</span>
                      <span className="text-white font-mono text-xs">{device.mac}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Estado:</span>
                      <span className="text-white">{device.state}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => toggleDeviceInternet(device)}
                    disabled={!device.ip}
                    className={`w-full px-4 py-2 rounded-lg font-medium transition ${
                      device.internet_status === 'permitted' || device.internet_status === 'limited'
                        ? 'bg-red-600 hover:bg-red-700 text-white'
                        : 'bg-gradient-to-r from-[#e00000] to-[#b80000] hover:from-[#ff0000] hover:to-[#e00000] text-white'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {device.internet_status === 'permitted' || device.internet_status === 'limited' ? 'Bloquear' : 'Permitir'}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-[#121212] border border-[#232323] rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-[#1a1a1a] border-b border-[#232323]">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Dispositivo</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">IP</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">MAC</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Estado</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Internet</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#232323]">
                  {filteredDevices.map((device, index) => (
                    <tr key={index} className="hover:bg-[#1a1a1a] transition">
                      <td className="px-4 py-3 text-white">{device.hostname || 'Sin nombre'}</td>
                      <td className="px-4 py-3 text-white font-mono text-sm">{device.ip || 'N/A'}</td>
                      <td className="px-4 py-3 text-white font-mono text-xs">{device.mac}</td>
                      <td className="px-4 py-3 text-white">{device.state}</td>
                      <td className="px-4 py-3">{getStatusBadge(device.internet_status)}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => toggleDeviceInternet(device)}
                          disabled={!device.ip}
                          className={`px-3 py-1 rounded text-sm font-medium transition ${
                            device.internet_status === 'permitted' || device.internet_status === 'limited'
                              ? 'bg-red-600 hover:bg-red-700 text-white'
                              : 'bg-[#e00000] hover:bg-[#ff0000] text-white'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {device.internet_status === 'permitted' || device.internet_status === 'limited' ? 'Bloquear' : 'Permitir'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {filteredDevices.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <Smartphone className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">No se encontraron dispositivos</p>
              <p className="text-sm mt-2">Haz clic en "Sincronizar" para cargar dispositivos del router</p>
            </div>
          )}
        </>
      )}

      <Modal
        isOpen={planModalOpen}
        onClose={() => {
          setPlanModalOpen(false);
          setPendingDevice(null);
        }}
        title="Seleccionar tipo de plan"
      >
        <div className="space-y-4">
          <p className="text-gray-300 text-sm">
            Selecciona si el plan es ilimitado o limitado para {pendingDevice?.hostname || pendingDevice?.ip}.
          </p>
          {planActionError && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-3 py-2 rounded text-sm">
              {planActionError}
            </div>
          )}
          <div className="flex gap-3">
            <button
              onClick={() => handleAllowDevice('permitted')}
              disabled={planActionLoading}
              className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {planActionLoading ? 'Procesando...' : 'Ilimitado'}
            </button>
            <button
              onClick={() => handleAllowDevice('limited')}
              disabled={planActionLoading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {planActionLoading ? 'Procesando...' : 'Limitado'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
