"""MikroTik SSH client using paramiko."""
from typing import Optional, Tuple

import paramiko

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class MikroTikSSHClient:
    """SSH fallback client for MikroTik RouterOS."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        timeout: int = 10,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.client: Optional[paramiko.SSHClient] = None

    def connect(self) -> bool:
        """Connect via SSH."""
        try:
            logger.info("mikrotik_ssh_connecting", host=self.host, port=self.port)

            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys()
            if settings.MT_SSH_KNOWN_HOSTS_FILE:
                self.client.load_host_keys(settings.MT_SSH_KNOWN_HOSTS_FILE)

            policy = paramiko.AutoAddPolicy() if settings.MT_SSH_ALLOW_UNKNOWN_HOSTS else paramiko.RejectPolicy()
            self.client.set_missing_host_key_policy(policy)

            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )

            logger.info("mikrotik_ssh_connected", host=self.host)
            return True
        except Exception as exc:
            logger.error("mikrotik_ssh_connection_failed", host=self.host, error=str(exc))
            self.client = None
            raise

    def disconnect(self):
        """Disconnect SSH."""
        if self.client:
            try:
                self.client.close()
                logger.info("mikrotik_ssh_disconnected", host=self.host)
            except Exception as exc:
                logger.warning("mikrotik_ssh_disconnect_error", error=str(exc))
            finally:
                self.client = None

    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Execute SSH command and return (stdout, stderr, exit_code)."""
        if not self.client:
            raise Exception("No hay conexion SSH activa. Llamar connect() primero.")

        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=self.timeout)
            stdout_text = stdout.read().decode("utf-8")
            stderr_text = stderr.read().decode("utf-8")
            exit_code = stdout.channel.recv_exit_status()

            if exit_code != 0:
                logger.warning("mikrotik_ssh_command_failed", exit_code=exit_code)

            return stdout_text, stderr_text, exit_code
        except Exception as exc:
            logger.error("mikrotik_ssh_execute_error", error=str(exc))
            raise

    def add_to_address_list(self, list_name: str, address: str, comment: Optional[str] = None) -> bool:
        """Add entry to address-list via SSH."""
        comment_part = f' comment="{comment}"' if comment else ""
        command = f"/ip firewall address-list add list={list_name} address={address}{comment_part}"

        stdout, stderr, exit_code = self.execute_command(command)
        return exit_code == 0

    def remove_from_address_list(self, list_name: str, address: str) -> bool:
        """Remove entry from address-list via SSH."""
        find_cmd = f"/ip firewall address-list print where list={list_name} and address={address}"
        stdout, stderr, exit_code = self.execute_command(find_cmd)

        if exit_code == 0 and stdout.strip():
            remove_cmd = f"/ip firewall address-list remove [find list={list_name} address={address}]"
            stdout, stderr, exit_code = self.execute_command(remove_cmd)
            return exit_code == 0

        return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
