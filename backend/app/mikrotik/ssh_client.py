"""Cliente SSH MikroTik usando paramiko"""
import paramiko
from typing import Optional, Tuple
from app.core.logging import get_logger

logger = get_logger(__name__)


class MikroTikSSHClient:
    """Cliente SSH para MikroTik RouterOS como fallback"""
    
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        timeout: int = 10
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None
    
    def connect(self) -> bool:
        """Conecta vía SSH"""
        try:
            logger.info("mikrotik_ssh_connecting", host=self.host, port=self.port)
            
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )
            
            logger.info("mikrotik_ssh_connected", host=self.host)
            return True
            
        except Exception as e:
            logger.error("mikrotik_ssh_connection_failed", host=self.host, error=str(e))
            self.client = None
            raise
    
    def disconnect(self):
        """Desconecta SSH"""
        if self.client:
            try:
                self.client.close()
                logger.info("mikrotik_ssh_disconnected", host=self.host)
            except Exception as e:
                logger.warning("mikrotik_ssh_disconnect_error", error=str(e))
            finally:
                self.client = None
    
    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Ejecuta comando SSH y retorna (stdout, stderr, exit_code)"""
        if not self.client:
            raise Exception("No hay conexión SSH activa. Llamar connect() primero.")
        
        try:
            logger.debug("mikrotik_ssh_execute", command=command)
            
            stdin, stdout, stderr = self.client.exec_command(command, timeout=self.timeout)
            
            stdout_text = stdout.read().decode('utf-8')
            stderr_text = stderr.read().decode('utf-8')
            exit_code = stdout.channel.recv_exit_status()
            
            if exit_code != 0:
                logger.warning("mikrotik_ssh_command_failed", 
                             command=command, 
                             exit_code=exit_code,
                             stderr=stderr_text)
            
            return stdout_text, stderr_text, exit_code
            
        except Exception as e:
            logger.error("mikrotik_ssh_execute_error", command=command, error=str(e))
            raise
    
    def add_to_address_list(self, list_name: str, address: str, comment: Optional[str] = None) -> bool:
        """Agrega entrada a address-list vía SSH"""
        comment_part = f' comment="{comment}"' if comment else ''
        command = f'/ip firewall address-list add list={list_name} address={address}{comment_part}'
        
        stdout, stderr, exit_code = self.execute_command(command)
        return exit_code == 0
    
    def remove_from_address_list(self, list_name: str, address: str) -> bool:
        """Elimina entrada de address-list vía SSH"""
        # Buscar ID y eliminar
        find_cmd = f'/ip firewall address-list print where list={list_name} and address={address}'
        stdout, stderr, exit_code = self.execute_command(find_cmd)
        
        if exit_code == 0 and stdout.strip():
            # Extraer ID (parsing simplificado)
            remove_cmd = f'/ip firewall address-list remove [find list={list_name} address={address}]'
            stdout, stderr, exit_code = self.execute_command(remove_cmd)
            return exit_code == 0
        
        return False
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
