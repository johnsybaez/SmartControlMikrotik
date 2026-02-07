"""Script de prueba para verificar la lógica de address lists"""

# Simulación de datos de MikroTik
mikrotik_entries = [
    {"list": "INET_LIMITADO", "address": "10.80.0.64", ".id": "*100"},
    {"list": "INET_BLOQUEADO", "address": "10.80.0.64", ".id": "*101"},
    {"list": "INET_PERMITIDO", "address": "10.80.0.20", ".id": "*102"},
]

print("=" * 60)
print("ESTADO INICIAL DE ADDRESS LISTS")
print("=" * 60)
for entry in mikrotik_entries:
    print(f"  {entry['list']:20} {entry['address']:15} ID: {entry['.id']}")
print()

def get_address_list(list_name=None):
    """Simula get_address_list"""
    if list_name:
        return [e for e in mikrotik_entries if e.get("list") == list_name]
    return mikrotik_entries

def remove_from_address_list_by_address(list_name, address):
    """Simula remove_from_address_list_by_address"""
    entries = get_address_list(list_name)
    removed_count = 0
    to_remove = []
    
    for entry in entries:
        if entry.get("address") == address:
            entry_id = entry.get(".id")
            if entry_id:
                to_remove.append(entry)
                removed_count += 1
                print(f"  ✓ Eliminando de {list_name}: {address} (ID: {entry_id})")
    
    # Remover de la lista
    for entry in to_remove:
        mikrotik_entries.remove(entry)
    
    if removed_count == 0:
        print(f"  ○ No se encontraron entradas en {list_name} para {address}")
    
    return removed_count

def add_to_address_list(list_name, address, comment=None):
    """Simula add_to_address_list con verificación de duplicados"""
    # Verificar si ya existe
    existing = get_address_list(list_name)
    for entry in existing:
        if entry.get("address") == address:
            print(f"  ⚠ La dirección {address} YA EXISTE en {list_name} (ID: {entry.get('.id')})")
            return entry
    
    # No existe, agregar nuevo
    new_id = f"*{len(mikrotik_entries) + 100}"
    new_entry = {
        "list": list_name,
        "address": address,
        ".id": new_id,
        "comment": comment
    }
    mikrotik_entries.append(new_entry)
    print(f"  → Agregado a {list_name}: {address} (ID: {new_id})")
    return new_entry

# SIMULAR BLOQUEO DE 10.80.0.64
print("=" * 60)
print("BLOQUEANDO 10.80.0.64 (está en INET_LIMITADO)")
print("=" * 60)

ip_address = "10.80.0.64"

# PASO 1: Limpiar de todas las listas
print("\nPASO 1: Limpiando de todas las listas...")
for list_to_clean in ["INET_PERMITIDO", "INET_LIMITADO", "INET_BLOQUEADO"]:
    removed_count = remove_from_address_list_by_address(list_to_clean, ip_address)

# PASO 2: Agregar a bloqueados
print("\nPASO 2: Agregando a INET_BLOQUEADO...")
add_to_address_list("INET_BLOQUEADO", ip_address, "Bloqueado por prueba")

# RESULTADO FINAL
print("\n" + "=" * 60)
print("ESTADO FINAL DE ADDRESS LISTS")
print("=" * 60)
for entry in mikrotik_entries:
    print(f"  {entry['list']:20} {entry['address']:15} ID: {entry['.id']}")

# Verificar que 10.80.0.64 solo está en INET_BLOQUEADO
print("\n" + "=" * 60)
print("VERIFICACIÓN")
print("=" * 60)
count_in_lists = {}
for entry in mikrotik_entries:
    if entry['address'] == ip_address:
        count_in_lists[entry['list']] = count_in_lists.get(entry['list'], 0) + 1

if len(count_in_lists) == 1 and "INET_BLOQUEADO" in count_in_lists:
    print(f"✅ CORRECTO: {ip_address} está SOLO en INET_BLOQUEADO")
else:
    print(f"❌ ERROR: {ip_address} está en múltiples listas: {count_in_lists}")
