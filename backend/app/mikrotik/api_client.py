"""Cliente API MikroTik usando routeros-api"""
import routeros_api
from typing import Optional, List, Dict, Any
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class MikroTikAPIClient:
    """Wrapper para routeros-api con manejo de errores y logging"""
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 8728,
        use_ssl: bool = False,
        ssl_verify: bool = False,
        timeout: int = 10
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        self.connection: Optional[routeros_api.RouterOsApiPool] = None
        
    def connect(self) -> bool:
        """Conecta al router MikroTik"""
        try:
            logger.info("mikrotik_api_connecting", host=self.host, port=self.port)
            
            self.connection = routeros_api.RouterOsApiPool(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                use_ssl=self.use_ssl,
                ssl_verify=self.ssl_verify,
                plaintext_login=True
            )
            
            # Test de conexión
            api = self.connection.get_api()
            system_resource = api.get_resource('/system/resource')
            system_resource.get()
            
            logger.info("mikrotik_api_connected", host=self.host)
            return True
            
        except Exception as e:
            logger.error("mikrotik_api_connection_failed", host=self.host, error=str(e))
            self.connection = None
            raise
    
    def disconnect(self):
        """Desconecta del router"""
        if self.connection:
            try:
                self.connection.disconnect()
                logger.info("mikrotik_api_disconnected", host=self.host)
            except Exception as e:
                logger.warning("mikrotik_api_disconnect_error", error=str(e))
            finally:
                self.connection = None
    
    def get_resource(self, path: str):
        """Obtiene un recurso de la API"""
        if not self.connection:
            raise Exception("No hay conexión activa. Llamar connect() primero.")
        
        api = self.connection.get_api()
        return api.get_resource(path)
    
    def execute(self, path: str, method: str = "get", params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Ejecuta comando en la API"""
        try:
            resource = self.get_resource(path)
            
            if method == "get":
                result = resource.get(**params) if params else resource.get()
            elif method == "add":
                result = resource.add(**params)
            elif method == "set":
                result = resource.set(**params)
            elif method == "remove":
                result = resource.remove(**params)
            else:
                raise ValueError(f"Método no soportado: {method}")
            
            return result if isinstance(result, list) else [result]
            
        except Exception as e:
            logger.error("mikrotik_api_execute_error", path=path, method=method, error=str(e))
            raise
    
    # === Métodos específicos ===
    
    def get_dhcp_leases(self, status: Optional[str] = None) -> List[Dict]:
        """Obtiene leases DHCP"""
        try:
            leases = self.execute("/ip/dhcp-server/lease", "get")
            
            if status:
                leases = [lease for lease in leases if lease.get("status") == status]
            
            return leases
        except Exception as e:
            logger.error("get_dhcp_leases_error", error=str(e))
            raise
    
    def get_address_list(self, list_name: Optional[str] = None) -> List[Dict]:
        """Obtiene entradas de address-list"""
        try:
            entries = self.execute("/ip/firewall/address-list", "get")
            
            if list_name:
                entries = [e for e in entries if e.get("list") == list_name]
            
            return entries
        except Exception as e:
            logger.error("get_address_list_error", error=str(e))
            raise
    
    def add_to_address_list(self, list_name: str, address: str, comment: Optional[str] = None) -> Dict:
        """Agrega entrada a address-list"""
        try:
            params = {
                "list": list_name,
                "address": address
            }
            if comment:
                params["comment"] = comment
            
            result = self.execute("/ip/firewall/address-list", "add", params)
            logger.info("address_list_added", list=list_name, address=address)
            return result
        except Exception as e:
            # Si falla porque ya existe, no es un error crítico
            if "already have" in str(e).lower() or "duplicate" in str(e).lower():
                logger.warning("address_already_exists", list=list_name, address=address)
                return {"status": "already_exists"}
            logger.error("add_address_list_error", list=list_name, address=address, error=str(e))
            raise
    
    def remove_from_address_list(self, entry_id: str) -> bool:
        """Elimina entrada de address-list por ID"""
        try:
            self.execute("/ip/firewall/address-list", "remove", {"id": entry_id})
            logger.info("address_list_removed", id=entry_id)
            return True
        except Exception as e:
            logger.error("remove_address_list_error", id=entry_id, error=str(e))
            raise
    
    def remove_from_address_list_by_address(self, list_name: str, address: str) -> int:
        """Elimina entrada(s) de address-list por nombre de lista y dirección
        
        Returns:
            int: Número de entradas eliminadas
        """
        try:
            # Buscar todas las entradas que coincidan
            entries = self.get_address_list(list_name)
            removed_count = 0
            
            for entry in entries:
                if entry.get("address") == address:
                    # Probar con ambos formatos: 'id' y '.id'
                    entry_id = entry.get("id") or entry.get(".id")
                    if entry_id:
                        try:
                            self.remove_from_address_list(entry_id)
                            removed_count += 1
                            logger.info("address_list_entry_removed", 
                                       list=list_name, 
                                       address=address, 
                                       id=entry_id)
                        except Exception as e:
                            logger.warning(f"No se pudo eliminar entrada {entry_id}: {e}")
            
            if removed_count > 0:
                logger.info("address_list_cleanup_complete", 
                           list=list_name, 
                           address=address, 
                           removed=removed_count)
            else:
                logger.debug("no_entries_found_to_remove", 
                            list=list_name, 
                            address=address)
            
            return removed_count
        except Exception as e:
            logger.error("remove_address_list_by_address_error", 
                        list=list_name, 
                        address=address, 
                        error=str(e))
            raise
    
    def get_simple_queues(self) -> List[Dict]:
        """Obtiene simple queues"""
        try:
            return self.execute("/queue/simple", "get")
        except Exception as e:
            logger.error("get_simple_queues_error", error=str(e))
            raise
    
    def add_simple_queue(
        self,
        name: str,
        target: str,
        max_limit: str,
        burst_limit: Optional[str] = None,
        burst_threshold: Optional[str] = None,
        burst_time: Optional[str] = None,
        priority: str = "8/8",
        comment: Optional[str] = None
    ) -> Dict:
        """Crea una simple queue"""
        try:
            params = {
                "name": name,
                "target": target,
                "max-limit": max_limit,
                "priority": priority
            }
            
            if burst_limit:
                params["burst-limit"] = burst_limit
            if burst_threshold:
                params["burst-threshold"] = burst_threshold
            if burst_time:
                params["burst-time"] = burst_time
            if comment:
                params["comment"] = comment
            
            result = self.execute("/queue/simple", "add", params)
            logger.info("simple_queue_added", name=name, target=target)
            return result
        except Exception as e:
            logger.error("add_simple_queue_error", name=name, error=str(e))
            raise
    
    def remove_simple_queue(self, queue_id: str) -> bool:
        """Elimina una simple queue"""
        try:
            self.execute("/queue/simple", "remove", {"id": queue_id})
            logger.info("simple_queue_removed", id=queue_id)
            return True
        except Exception as e:
            logger.error("remove_simple_queue_error", id=queue_id, error=str(e))
            raise
    
    def get_system_resource(self) -> Dict:
        """Obtiene recursos del sistema (uptime, version, etc)"""
        try:
            result = self.execute("/system/resource", "get")
            return result[0] if result else {}
        except Exception as e:
            logger.error("get_system_resource_error", error=str(e))
            raise
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
