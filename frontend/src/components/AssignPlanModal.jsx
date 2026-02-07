import { useState, useEffect } from 'react';
import { Zap, Check } from 'lucide-react';
import Modal from './Modal';
import api from '../services/api';

export default function AssignPlanModal({ isOpen, onClose, device, onSuccess }) {
  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      fetchPlans();
    }
  }, [isOpen]);

  const fetchPlans = async () => {
    try {
      const response = await api.get('/plans?active_only=true');
      setPlans(response.data);
    } catch (err) {
      setError('Error al cargar planes: ' + err.message);
      console.error('Error fetching plans:', err);
    }
  };

  const handleAssignPlan = async () => {
    if (!selectedPlan) {
      setError('Por favor selecciona un plan');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await api.post('/qos/assign-plan', {
        device_id: device.id,
        plan_id: selectedPlan.id
      });
      onSuccess();
      onClose();
    } catch (err) {
      setError('Error al asignar plan: ' + err.message);
      console.error('Error assigning plan:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatSpeed = (bps) => {
    const mbps = bps / 1000000;
    return `${mbps} Mbps`;
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Asignar Plan de Servicio">
      <div className="space-y-4">
        {device && (
          <div className="bg-[#1a1a1a] border border-[#232323] rounded-lg p-4">
            <p className="text-gray-400 text-sm mb-1">Dispositivo:</p>
            <p className="text-white font-medium">{device.hostname || device.name || 'Sin nombre'}</p>
            <p className="text-gray-500 text-sm mt-1">{device.ip || device.ip_address}</p>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-500 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <div className="space-y-3 max-h-96 overflow-y-auto">
          {plans.map((plan) => (
            <div
              key={plan.id}
              onClick={() => setSelectedPlan(plan)}
              className={`border rounded-lg p-4 cursor-pointer transition ${
                selectedPlan?.id === plan.id
                  ? 'border-[#e00000] bg-[#e00000]/10'
                  : 'border-[#232323] bg-[#1a1a1a] hover:border-[#e00000]/50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    selectedPlan?.id === plan.id ? 'bg-[#e00000]' : 'bg-[#232323]'
                  }`}>
                    <Zap className={`w-5 h-5 ${
                      selectedPlan?.id === plan.id ? 'text-white' : 'text-gray-400'
                    }`} />
                  </div>
                  <div>
                    <h4 className="font-semibold text-white">{plan.name}</h4>
                    <p className="text-sm text-gray-400 mt-1">{plan.description}</p>
                  </div>
                </div>
                {selectedPlan?.id === plan.id && (
                  <Check className="w-5 h-5 text-[#e00000]" />
                )}
              </div>

              <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
                <div>
                  <p className="text-gray-500">Descarga</p>
                  <p className="text-green-400 font-medium">{formatSpeed(plan.download_speed)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Carga</p>
                  <p className="text-blue-400 font-medium">{formatSpeed(plan.upload_speed)}</p>
                </div>
                <div>
                  <p className="text-gray-500">Precio</p>
                  <p className="text-[#e00000] font-bold">${parseFloat(plan.price).toFixed(2)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {plans.length === 0 && (
          <div className="text-center py-8">
            <Zap className="w-12 h-12 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-400">No hay planes disponibles</p>
          </div>
        )}

        <div className="flex gap-3 pt-4 border-t border-[#232323]">
          <button
            onClick={onClose}
            className="flex-1 bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded-lg transition"
          >
            Cancelar
          </button>
          <button
            onClick={handleAssignPlan}
            disabled={!selectedPlan || loading}
            className="flex-1 bg-gradient-to-r from-[#e00000] to-[#b80000] hover:from-[#ff0000] hover:to-[#e00000] text-white px-4 py-2 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Asignando...' : 'Asignar Plan'}
          </button>
        </div>
      </div>
    </Modal>
  );
}
