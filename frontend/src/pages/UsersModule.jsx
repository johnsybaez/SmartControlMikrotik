import { useEffect, useState } from 'react';
import { Users, KeyRound, ShieldAlert } from 'lucide-react';
import api from '../services/api';
import useAuthStore from '../store/authStore';
import Modal from '../components/Modal';

export default function UsersModule() {
  const { user } = useAuthStore();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState('list');
  const [form, setForm] = useState({
    username: '',
    password: '',
    full_name: '',
    email: '',
    role: 'operator',
    is_active: true
  });

  useEffect(() => {
    if (user?.role === 'admin') {
      loadUsers();
    }
  }, [user?.role]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/users');
      setUsers(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const openPasswordModal = (targetUser) => {
    setSelectedUser(targetUser);
    setNewPassword('');
    setShowModal(true);
  };

  const handleChangePassword = async () => {
    if (!selectedUser) return;
    if (selectedUser.username === 'admin') {
      const confirmChange = confirm(
        'Advertencia: si cambias la clave de admin, dejará de ser la credencial por defecto.'
      );
      if (!confirmChange) {
        return;
      }
    }

    try {
      setLoading(true);
      await api.put(`/api/users/${selectedUser.id}/password`, {
        new_password: newPassword
      });
      setShowModal(false);
      await loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async () => {
    setError(null);
    try {
      setLoading(true);
      await api.post('/api/users', {
        username: form.username,
        password: form.password,
        full_name: form.full_name || null,
        email: form.email || null,
        role: form.role,
        is_active: form.is_active
      });
      setForm({
        username: '',
        password: '',
        full_name: '',
        email: '',
        role: 'operator',
        is_active: true
      });
      await loadUsers();
      setActiveTab('list');
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (targetUser) => {
    if (!targetUser) return;
    setError(null);

    if (targetUser.username === 'admin' && targetUser.is_active) {
      const confirmDeactivate = confirm(
        'Advertencia: si desactivas admin, no podrás iniciar sesión con esa cuenta.'
      );
      if (!confirmDeactivate) return;
    }

    try {
      setLoading(true);
      await api.put(`/api/users/${targetUser.id}`, {
        is_active: !targetUser.is_active
      });
      await loadUsers();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  if (user?.role !== 'admin') {
    return (
      <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
        <h1 className="text-2xl font-bold text-white">Usuarios</h1>
        <p className="text-gray-400 mt-2">No tienes permisos para acceder a este módulo.</p>
      </div>
    );
  }

  return (
    <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Usuarios</h1>
          <p className="text-gray-400 mt-1">Gestión de roles y credenciales</p>
        </div>
        <button
          onClick={loadUsers}
          className="bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded-lg"
        >
          Actualizar
        </button>
      </div>

      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setActiveTab('list')}
          className={`px-4 py-2 rounded-lg border transition ${
            activeTab === 'list'
              ? 'bg-[#e00000]/20 border-[#e00000] text-white'
              : 'bg-[#121212] border-[#232323] text-gray-400 hover:text-white'
          }`}
        >
          Usuarios creados
        </button>
        <button
          onClick={() => setActiveTab('create')}
          className={`px-4 py-2 rounded-lg border transition ${
            activeTab === 'create'
              ? 'bg-[#e00000]/20 border-[#e00000] text-white'
              : 'bg-[#121212] border-[#232323] text-gray-400 hover:text-white'
          }`}
        >
          Creación de usuario
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
          <p className="text-gray-400 mt-4">Cargando usuarios...</p>
        </div>
      ) : (
        <>
          {activeTab === 'list' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {users.map((u) => (
                <div key={u.id} className="bg-[#121212] border border-[#232323] rounded-lg p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="bg-[#e00000]/20 p-3 rounded-full">
                      <Users className="w-6 h-6 text-[#e00000]" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-lg">{u.username}</h3>
                      <p className="text-sm text-gray-400">{u.full_name || 'Sin nombre'}</p>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm mb-4">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Rol:</span>
                      <span className="text-white font-medium">{u.role}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Estado:</span>
                      <span className={u.is_active ? 'text-green-400' : 'text-red-400'}>
                        {u.is_active ? 'Activo' : 'Inactivo'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Email:</span>
                      <span className="text-white">{u.email || 'N/A'}</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    <button
                      onClick={() => openPasswordModal(u)}
                      className="w-full bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded text-sm flex items-center justify-center gap-2"
                    >
                      <KeyRound className="w-4 h-4" />
                      Cambiar clave
                    </button>
                    <button
                      onClick={() => handleToggleActive(u)}
                      disabled={loading}
                      className={`w-full px-4 py-2 rounded text-sm flex items-center justify-center gap-2 border transition ${
                        u.is_active
                          ? 'bg-red-600/20 border-red-600 text-red-300 hover:bg-red-600/30'
                          : 'bg-green-600/20 border-green-600 text-green-300 hover:bg-green-600/30'
                      } ${loading ? 'opacity-60 cursor-not-allowed' : ''}`}
                    >
                      {u.is_active ? 'Desactivar' : 'Activar'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'create' && (
            <div className="bg-[#121212] border border-[#232323] rounded-lg p-6">
              <h2 className="text-lg font-semibold text-white mb-4">Creación de usuario</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <input
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  placeholder="Usuario"
                  className="px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                />
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  placeholder="Contraseña"
                  className="px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                />
                <input
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="Nombre completo"
                  className="px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                />
                <input
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="Email"
                  className="px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                />
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                >
                  <option value="admin">Administrador</option>
                  <option value="operator">Operador</option>
                </select>
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                  />
                  Activo
                </label>
              </div>
              <button
                onClick={handleCreateUser}
                disabled={loading || !form.username || !form.password}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
              >
                {loading ? 'Guardando...' : 'Crear usuario'}
              </button>
            </div>
          )}
        </>
      )}

      <Modal isOpen={showModal} onClose={() => setShowModal(false)} title="Cambiar clave">
        <div className="space-y-4">
          {selectedUser?.username === 'admin' && (
            <div className="bg-yellow-500/10 border border-yellow-500/50 text-yellow-400 px-4 py-3 rounded-lg text-sm flex gap-2">
              <ShieldAlert className="w-4 h-4 mt-0.5" />
              Cambiar la clave de admin elimina la credencial por defecto.
            </div>
          )}
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="Nueva contraseña"
            className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
          />
          <div className="flex gap-3 pt-2">
            <button
              onClick={() => setShowModal(false)}
              className="flex-1 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded-lg"
            >
              Cancelar
            </button>
            <button
              onClick={handleChangePassword}
              disabled={!newPassword || loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg disabled:opacity-50"
            >
              Guardar
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
