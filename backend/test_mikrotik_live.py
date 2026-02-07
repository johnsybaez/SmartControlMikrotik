"""Script de prueba para conectar al MikroTik"""
import sys
sys.path.insert(0, 'C:\\SmartControl\\backend')

from app.mikrotik.client import MikroTikClient
from app.core.logging import get_logger

logger = get_logger(__name__)

def test_mikrotik():
    """Prueba conexión con MikroTik"""
    
    print("\n" + "="*60)
    print("PRUEBA DE CONEXIÓN MIKROTIK")
    print("="*60)
    
    config = {
        'host': '10.80.0.1',
        'username': 'portal',
        'password': 'Porta123!!',
        'api_port': 8728,
        'ssh_port': 2214,
        'use_ssl': False,
        'ssl_verify': False,
        'timeout': 10
    }
    
    print(f"\nConectando a: {config['host']}:{config['api_port']}")
    print(f"Usuario: {config['username']}")
    
    try:
        with MikroTikClient(**config) as client:
            print(f"\n✓ Conexión exitosa vía {client.method_used}")
            
            # Test 1: System Resource
            print("\n" + "-"*60)
            print("TEST 1: Información del Sistema")
            print("-"*60)
            system_info = client.get_system_resource()
            print(f"Versión: {system_info.get('version', 'N/A')}")
            print(f"Board: {system_info.get('board-name', 'N/A')}")
            print(f"Uptime: {system_info.get('uptime', 'N/A')}")
            print(f"CPU Load: {system_info.get('cpu-load', 'N/A')}%")
            print(f"Memoria Libre: {system_info.get('free-memory', 'N/A')}")
            print(f"Memoria Total: {system_info.get('total-memory', 'N/A')}")
            
            # Test 2: Address Lists
            print("\n" + "-"*60)
            print("TEST 2: Address Lists (INET_PERMITIDO)")
            print("-"*60)
            permitidos = client.get_address_list("INET_PERMITIDO")
            print(f"Total entradas PERMITIDO: {len(permitidos)}")
            for i, entry in enumerate(permitidos[:5], 1):
                print(f"  {i}. {entry.get('address', 'N/A')} - {entry.get('comment', 'Sin comentario')}")
            if len(permitidos) > 5:
                print(f"  ... y {len(permitidos) - 5} más")
            
            print("\n" + "-"*60)
            print("TEST 3: Address Lists (INET_BLOQUEADO)")
            print("-"*60)
            bloqueados = client.get_address_list("INET_BLOQUEADO")
            print(f"Total entradas BLOQUEADO: {len(bloqueados)}")
            for i, entry in enumerate(bloqueados[:5], 1):
                print(f"  {i}. {entry.get('address', 'N/A')} - {entry.get('comment', 'Sin comentario')}")
            if len(bloqueados) > 5:
                print(f"  ... y {len(bloqueados) - 5} más")
            
            # Test 3: DHCP Leases
            print("\n" + "-"*60)
            print("TEST 4: DHCP Leases (bound)")
            print("-"*60)
            leases = client.get_dhcp_leases(status="bound")
            print(f"Total leases activos: {len(leases)}")
            for i, lease in enumerate(leases[:10], 1):
                mac = lease.get('mac-address', 'N/A')
                ip = lease.get('address', 'N/A')
                hostname = lease.get('host-name', 'Sin nombre')
                print(f"  {i}. {ip:15s} | {mac:17s} | {hostname}")
            if len(leases) > 10:
                print(f"  ... y {len(leases) - 10} más")
            
            # Test 4: Simple Queues
            print("\n" + "-"*60)
            print("TEST 5: Simple Queues")
            print("-"*60)
            queues = client.get_simple_queues()
            print(f"Total queues: {len(queues)}")
            for i, queue in enumerate(queues[:5], 1):
                name = queue.get('name', 'N/A')
                target = queue.get('target', 'N/A')
                max_limit = queue.get('max-limit', 'N/A')
                print(f"  {i}. {name:20s} | {target:15s} | {max_limit}")
            if len(queues) > 5:
                print(f"  ... y {len(queues) - 5} más")
            
            print("\n" + "="*60)
            print("✓ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
            print(f"  Método usado: {client.method_used}")
            print("="*60 + "\n")
            
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = test_mikrotik()
    sys.exit(0 if success else 1)
