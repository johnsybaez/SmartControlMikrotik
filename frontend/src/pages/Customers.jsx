import { Users, Plus, Search, Mail, Phone, MapPin } from 'lucide-react';
import { useState } from 'react';

export default function Customers() {
  const [searchTerm, setSearchTerm] = useState('');
  const [customers] = useState([
    {
      id: 1,
      name: 'Juan Pérez',
      email: 'juan.perez@email.com',
      phone: '+1 809-555-0101',
      address: 'Calle Principal #123',
      plan: 'Plan Premium',
      status: 'active',
    },
    {
      id: 2,
      name: 'María González',
      email: 'maria.gonzalez@email.com',
      phone: '+1 809-555-0102',
      address: 'Avenida Central #456',
      plan: 'Plan Estándar',
      status: 'active',
    },
    {
      id: 3,
      name: 'Carlos Rodríguez',
      email: 'carlos.rodriguez@email.com',
      phone: '+1 809-555-0103',
      address: 'Calle Secundaria #789',
      plan: 'Plan Básico',
      status: 'inactive',
    },
  ]);

  const filteredCustomers = customers.filter(customer =>
    customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    customer.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    customer.phone.includes(searchTerm)
  );

  return (
    <div className="p-6 bg-gradient-to-br from-[#0b0b0b] to-[#1a0000] min-h-full">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Clientes</h1>
          <p className="text-gray-400 mt-1">Gestión de clientes y suscripciones</p>
        </div>
        <button className="bg-gradient-to-r from-[#e00000] to-[#b80000] hover:from-[#ff0000] hover:to-[#e00000] text-white px-4 py-2 rounded-lg flex items-center gap-2 shadow-lg shadow-[#e00000]/30">
          <Plus className="w-5 h-5" />
          Nuevo Cliente
        </button>
      </div>

      {/* Search Bar */}
      <div className="bg-[#121212] border border-[#232323] rounded-lg shadow-lg p-4 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Buscar por nombre, email o teléfono..."
            className="w-full pl-10 pr-4 py-2 bg-[#0f0f0f] border border-[#2a2a2a] text-white rounded-lg focus:ring-2 focus:ring-[#e00000] focus:border-transparent outline-none"
          />
        </div>
      </div>

      {/* Customers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredCustomers.map((customer) => (
          <div key={customer.id} className="bg-[#121212] border border-[#232323] rounded-lg p-6 hover:border-[#e00000] transition-colors shadow-lg">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="bg-[#e00000] bg-opacity-20 p-3 rounded-full">
                  <Users className="w-6 h-6 text-[#e00000]" />
                </div>
                <div>
                  <h3 className="font-semibold text-white text-lg">{customer.name}</h3>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    customer.status === 'active'
                      ? 'bg-green-500/20 text-green-400'
                      : 'bg-red-500/20 text-red-400'
                  }`}>
                    {customer.status === 'active' ? 'Activo' : 'Inactivo'}
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-2 text-sm">
                <Mail className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">{customer.email}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Phone className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">{customer.phone}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="w-4 h-4 text-gray-400" />
                <span className="text-gray-300">{customer.address}</span>
              </div>
              <div className="flex justify-between text-sm border-t border-[#232323] pt-3">
                <span className="text-gray-400">Plan:</span>
                <span className="font-medium text-[#e00000]">{customer.plan}</span>
              </div>
            </div>

            <button className="w-full bg-[#1a1a1a] hover:bg-[#2a2a2a] border border-[#232323] text-white px-4 py-2 rounded text-sm font-medium">
              Ver Detalles
            </button>
          </div>
        ))}
      </div>

      {filteredCustomers.length === 0 && (
        <div className="text-center py-12">
          <Users className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-400 mb-2">No se encontraron clientes</h3>
          <p className="text-gray-500">Intenta con otros términos de búsqueda</p>
        </div>
      )}
    </div>
  );
}
