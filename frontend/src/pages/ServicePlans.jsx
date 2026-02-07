import { Zap, Plus, Edit, Trash2 } from 'lucide-react';
import { useState, useEffect } from 'react';
import api from '../services/api';
import Modal from '../components/Modal';

export default function ServicePlans() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [editError, setEditError] = useState(null);
  const [createError, setCreateError] = useState(null);
  const [editForm, setEditForm] = useState({
    id: null,
    name: '',
    description: '',
    download_limit: '',
    upload_limit: '',
    priority: 8,
    is_active: true,
  });
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    download_limit: '',
    upload_limit: '',
    priority: 8,
    is_active: true,
  });

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/plans');
      setPlans(response.data);
    } catch (err) {
      setError('Error al cargar planes: ' + err.message);
      console.error('Error fetching plans:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatSpeed = (bps) => {
    const mbps = bps / 1000000;
    return `${mbps} Mbps`;
  };

  const openEditModal = (plan) => {
    setEditForm({
      id: plan.id,
      name: plan.name || '',
      description: plan.description || '',
      download_limit: plan.download_limit || '',
      upload_limit: plan.upload_limit || '',
      priority: plan.priority ?? 8,
      is_active: plan.is_active ?? true,
    });
    setEditError(null);
    setIsEditOpen(true);
  };

  const closeEditModal = () => {
    if (isSaving) return;
    setIsEditOpen(false);
  };

  const openCreateModal = () => {
    setCreateForm({
      name: '',
      description: '',
      download_limit: '',
      upload_limit: '',
      priority: 8,
      is_active: true,
    });
    setCreateError(null);
    setIsCreateOpen(true);
  };

  const closeCreateModal = () => {
    if (isSaving) return;
    setIsCreateOpen(false);
  };

  const handleEditChange = (field, value) => {
    setEditForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleCreateChange = (field, value) => {
    setCreateForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const saveEdit = async (e) => {
    e.preventDefault();
    if (!editForm.id) return;
    setIsSaving(true);
    setEditError(null);
    try {
      await api.put(`/api/plans/${editForm.id}`, {
        name: editForm.name,
        description: editForm.description,
        download_limit: editForm.download_limit,
        upload_limit: editForm.upload_limit,
        priority: Number(editForm.priority),
        is_active: Boolean(editForm.is_active),
      });
      setIsEditOpen(false);
      fetchPlans();
    } catch (err) {
      setEditError('Error al guardar cambios: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const saveCreate = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    setCreateError(null);
    try {
      await api.post('/api/plans', {
        name: createForm.name,
        description: createForm.description,
        download_limit: createForm.download_limit,
        upload_limit: createForm.upload_limit,
        priority: Number(createForm.priority),
        is_active: Boolean(createForm.is_active),
      });
      setIsCreateOpen(false);
      fetchPlans();
    } catch (err) {
      setCreateError('Error al crear plan: ' + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (plan) => {
    const confirmed = window.confirm(`¿Eliminar el plan "${plan.name}"?`);
    if (!confirmed) return;
    setError(null);
    try {
      await api.delete(`/api/plans/${plan.id}`);
      fetchPlans();
    } catch (err) {
      setError('Error al eliminar plan: ' + err.message);
    }
  };

  return (
    <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Control de Ancho de Banda</h1>
          <p className="text-gray-400 mt-1">Gestión de planes de QoS y velocidad</p>
        </div>
        <button
          onClick={openCreateModal}
          className="bg-gradient-to-r from-[#e00000] to-[#b80000] hover:from-[#ff0000] hover:to-[#e00000] text-white px-4 py-2 rounded-lg flex items-center gap-2 shadow-lg shadow-[#e00000]/30"
        >
          <Plus className="w-5 h-5" />
          Nuevo Plan
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
          <p className="text-gray-400 mt-4">Cargando planes...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((plan) => (
            <div key={plan.id} className="bg-[#121212] border border-[#232323] rounded-lg p-6 hover:border-[#e00000] transition-colors shadow-lg">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="bg-[#e00000] bg-opacity-20 p-3 rounded-lg">
                    <Zap className="w-6 h-6 text-[#e00000]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-lg">{plan.name}</h3>
                    <p className="text-sm text-gray-400">{plan.description}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-3 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Descarga:</span>
                  <span className="font-medium text-green-400">{plan.download_limit}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Carga:</span>
                  <span className="font-medium text-blue-400">{plan.upload_limit}</span>
                </div>
                <div className="flex justify-between text-sm border-t border-[#232323] pt-3">
                  <span className="text-gray-400">Prioridad:</span>
                  <span className="font-bold text-[#e00000] text-lg">{plan.priority || 8}</span>
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => openEditModal(plan)}
                  className="flex-1 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-3 py-2 rounded text-sm font-medium flex items-center justify-center gap-2"
                >
                  <Edit className="w-4 h-4" />
                  Editar
                </button>
                <button
                  onClick={() => handleDelete(plan)}
                  className="bg-[#3b1212] hover:bg-[#4b1212] border border-[#ff6c6c] text-white px-3 py-2 rounded text-sm"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && plans.length === 0 && (
        <div className="text-center py-12">
          <Zap className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-400 mb-2">No hay planes configurados</h3>
          <p className="text-gray-500">Agrega tu primer plan de servicio para comenzar</p>
        </div>
      )}

      <Modal isOpen={isEditOpen} onClose={closeEditModal} title="Editar plan">
        <form onSubmit={saveEdit} className="space-y-4">
          {editError && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-500 px-3 py-2 rounded text-sm">
              {editError}
            </div>
          )}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Nombre</label>
            <input
              value={editForm.name}
              onChange={(e) => handleEditChange('name', e.target.value)}
              className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Descripción</label>
            <input
              value={editForm.description}
              onChange={(e) => handleEditChange('description', e.target.value)}
              className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Descarga</label>
              <input
                value={editForm.download_limit}
                onChange={(e) => handleEditChange('download_limit', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="Ej: 10M"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Carga</label>
              <input
                value={editForm.upload_limit}
                onChange={(e) => handleEditChange('upload_limit', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="Ej: 5M"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Prioridad</label>
              <input
                type="number"
                min="1"
                max="8"
                value={editForm.priority}
                onChange={(e) => handleEditChange('priority', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Estado</label>
              <select
                value={editForm.is_active ? 'true' : 'false'}
                onChange={(e) => handleEditChange('is_active', e.target.value === 'true')}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
              >
                <option value="true">Activo</option>
                <option value="false">Inactivo</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={closeEditModal}
              className="flex-1 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded-lg"
              disabled={isSaving}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 bg-gradient-to-r from-[#e00000] to-[#b80000] hover:from-[#ff0000] hover:to-[#e00000] text-white px-4 py-2 rounded-lg"
              disabled={isSaving}
            >
              {isSaving ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={isCreateOpen} onClose={closeCreateModal} title="Nuevo plan">
        <form onSubmit={saveCreate} className="space-y-4">
          {createError && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-500 px-3 py-2 rounded text-sm">
              {createError}
            </div>
          )}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Nombre</label>
            <input
              value={createForm.name}
              onChange={(e) => handleCreateChange('name', e.target.value)}
              className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Descripción</label>
            <input
              value={createForm.description}
              onChange={(e) => handleCreateChange('description', e.target.value)}
              className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Descarga</label>
              <input
                value={createForm.download_limit}
                onChange={(e) => handleCreateChange('download_limit', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="Ej: 10M"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Carga</label>
              <input
                value={createForm.upload_limit}
                onChange={(e) => handleCreateChange('upload_limit', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
                placeholder="Ej: 5M"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Prioridad</label>
              <input
                type="number"
                min="1"
                max="8"
                value={createForm.priority}
                onChange={(e) => handleCreateChange('priority', e.target.value)}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Estado</label>
              <select
                value={createForm.is_active ? 'true' : 'false'}
                onChange={(e) => handleCreateChange('is_active', e.target.value === 'true')}
                className="w-full px-3 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg"
              >
                <option value="true">Activo</option>
                <option value="false">Inactivo</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={closeCreateModal}
              className="flex-1 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded-lg"
              disabled={isSaving}
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="flex-1 bg-gradient-to-r from-[#e00000] to-[#b80000] hover:from-[#ff0000] hover:to-[#e00000] text-white px-4 py-2 rounded-lg"
              disabled={isSaving}
            >
              {isSaving ? 'Guardando...' : 'Crear'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
