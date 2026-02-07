"""Orquestador de clientes MikroTik con Circuit Breaker"""
from enum import Enum
from typing import Optional, Any, Callable
from datetime import datetime, timedelta
from app.mikrotik.api_client import MikroTikAPIClient
from app.mikrotik.ssh_client import MikroTikSSHClient
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class CircuitState(Enum):
    """Estados del circuit breaker"""
    CLOSED = "closed"  # API funcionando normal
    OPEN = "open"  # API falló, usando SSH
    HALF_OPEN = "half_open"  # Probando reconexión a API


class CircuitBreaker:
    """Circuit Breaker para API → SSH fallback"""
    
    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_seconds: int = 300,
        half_open_max_calls: int = 1
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at: Optional[datetime] = None
        self.half_open_calls = 0
    
    def record_success(self):
        """Registra éxito (reset)"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.opened_at = None
        self.half_open_calls = 0
        logger.info("circuit_breaker_closed")
    
    def record_failure(self):
        """Registra fallo"""
        self.failure_count += 1
        logger.warning("circuit_breaker_failure", count=self.failure_count)
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.utcnow()
            logger.error("circuit_breaker_opened", failures=self.failure_count)
    
    def can_attempt_api(self) -> bool:
        """Determina si se puede intentar API"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Verificar si pasó el timeout
            if self.opened_at and datetime.utcnow() - self.opened_at > timedelta(seconds=self.timeout_seconds):
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("circuit_breaker_half_open")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return False


class MikroTikClient:
    """Cliente unificado con API-first y SSH fallback"""
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        api_port: int = 8728,
        ssh_port: int = 22,
        use_ssl: bool = False,
        ssl_verify: bool = False,
        timeout: int = 10
    ):
        self.host = host
        self.username = username
        self.password = password
        self.api_port = api_port
        self.ssh_port = ssh_port
        self.use_ssl = use_ssl
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=settings.CIRCUIT_FAILURE_THRESHOLD,
            timeout_seconds=settings.CIRCUIT_TIMEOUT_SECONDS,
            half_open_max_calls=settings.CIRCUIT_HALF_OPEN_MAX_CALLS
        )
        
        # Clientes
        self.api_client: Optional[MikroTikAPIClient] = None
        self.ssh_client: Optional[MikroTikSSHClient] = None
        self.method_used: str = "UNKNOWN"
    
    def _execute_with_fallback(self, api_func: Callable, ssh_func: Optional[Callable] = None) -> Any:
        """Ejecuta función con fallback API → SSH"""
        
        # Intentar API si circuit breaker lo permite
        if self.circuit_breaker.can_attempt_api():
            try:
                if not self.api_client:
                    self.api_client = MikroTikAPIClient(
                        host=self.host,
                        username=self.username,
                        password=self.password,
                        port=self.api_port,
                        use_ssl=self.use_ssl,
                        ssl_verify=self.ssl_verify,
                        timeout=self.timeout
                    )
                    self.api_client.connect()
                
                result = api_func(self.api_client)
                self.circuit_breaker.record_success()
                self.method_used = "API"
                return result
                
            except Exception as e:
                logger.warning("api_execution_failed", error=str(e))
                self.circuit_breaker.record_failure()
                
                # Limpiar cliente API fallido
                if self.api_client:
                    try:
                        self.api_client.disconnect()
                    except:
                        pass
                    self.api_client = None
        
        # Fallback a SSH
        if ssh_func:
            try:
                logger.info("using_ssh_fallback", host=self.host)
                
                if not self.ssh_client:
                    self.ssh_client = MikroTikSSHClient(
                        host=self.host,
                        username=self.username,
                        password=self.password,
                        port=self.ssh_port,
                        timeout=self.timeout
                    )
                    self.ssh_client.connect()
                
                result = ssh_func(self.ssh_client)
                self.method_used = "SSH"
                return result
                
            except Exception as e:
                logger.error("ssh_execution_failed", error=str(e))
                raise
        else:
            raise Exception("API falló y no hay función SSH de fallback")
    
    def get_dhcp_leases(self, status: Optional[str] = None):
        """Obtiene leases DHCP"""
        return self._execute_with_fallback(
            lambda client: client.get_dhcp_leases(status),
            None  # SSH no soportado para leases en MVP
        )
    
    def get_address_list(self, list_name: Optional[str] = None):
        """Obtiene address-list"""
        return self._execute_with_fallback(
            lambda client: client.get_address_list(list_name),
            None
        )
    
    def add_to_address_list(self, list_name: str, address: str, comment: Optional[str] = None):
        """Agrega a address-list"""
        return self._execute_with_fallback(
            lambda client: client.add_to_address_list(list_name, address, comment),
            lambda client: client.add_to_address_list(list_name, address, comment)
        )
    
    def remove_from_address_list(self, list_name: str, address: str):
        """Elimina de address-list por nombre de lista y dirección"""
        return self._execute_with_fallback(
            lambda client: client.remove_from_address_list_by_address(list_name, address),
            lambda client: client.remove_from_address_list(list_name, address) if hasattr(client, 'remove_from_address_list') else 0
        )
    
    def get_simple_queues(self):
        """Obtiene simple queues"""
        return self._execute_with_fallback(
            lambda client: client.get_simple_queues(),
            None
        )
    
    def add_simple_queue(self, **kwargs):
        """Crea simple queue"""
        return self._execute_with_fallback(
            lambda client: client.add_simple_queue(**kwargs),
            None
        )
    
    def remove_simple_queue(self, queue_id: str):
        """Elimina simple queue"""
        return self._execute_with_fallback(
            lambda client: client.remove_simple_queue(queue_id),
            None
        )
    
    def get_system_resource(self):
        """Obtiene recursos del sistema"""
        return self._execute_with_fallback(
            lambda client: client.get_system_resource(),
            None
        )
    
    def disconnect(self):
        """Desconecta todos los clientes"""
        if self.api_client:
            try:
                self.api_client.disconnect()
            except:
                pass
        
        if self.ssh_client:
            try:
                self.ssh_client.disconnect()
            except:
                pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
