"""Application configuration"""
from pathlib import Path
from typing import List
import os

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)


class Settings(BaseSettings):
    """Application configuration"""

    APP_NAME: str = "SmartControl"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = False

    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,https://localhost:5173,https://localhost:5174"
    CORS_CREDENTIALS: bool = True
    TRUSTED_HOSTS: str = "localhost,127.0.0.1"
    ENABLE_SECURITY_HEADERS: bool = True
    FORCE_HTTPS: bool = False
    SESSION_COOKIE_NAME: str = "smartcontrol_session"
    CSRF_COOKIE_NAME: str = "smartcontrol_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"
    CSRF_PROTECTION_ENABLED: bool = True

    DATABASE_URL: str = "sqlite:///./smartbjportal.db"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/smartcontrol.log"
    LOG_MAX_BYTES: int = 10485760
    LOG_BACKUP_COUNT: int = 5
    LOG_FORMAT: str = "json"

    MT_HOST: str = "10.80.0.1"
    MT_PORT: int = 8728
    MT_SSH_PORT: int = 2214
    MT_USER: str = ""
    MT_PASS: str = ""
    MT_USE_SSL: bool = False
    MT_SSL_VERIFY: bool = False
    MT_SSH_ALLOW_UNKNOWN_HOSTS: bool = False
    MT_SSH_KNOWN_HOSTS_FILE: str = ""
    MT_TIMEOUT: int = 10
    ROUTER_CREDENTIALS_KEY: str = ""

    LIST_PERMITIDO: str = "INET_PERMITIDO"
    LIST_LIMITADO: str = "INET_LIMITADO"
    LIST_BLOQUEADO: str = "INET_BLOQUEADO"

    CIRCUIT_FAILURE_THRESHOLD: int = 3
    CIRCUIT_TIMEOUT_SECONDS: int = 300
    CIRCUIT_HALF_OPEN_MAX_CALLS: int = 1

    STATS_COLLECTION_INTERVAL_MINUTES: int = 60
    STATS_RETENTION_DAYS: int = 90
    REPORTS_TEMP_DIR: str = "/tmp/smartcontrol_reports"

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD_SECONDS: int = 60
    RATE_LIMIT_LOGIN: str = "5/minute"

    BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_PATH: str = "./backups"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def trusted_hosts_list(self) -> List[str]:
        return [host.strip() for host in self.TRUSTED_HOSTS.split(",") if host.strip()]

    @field_validator("ENVIRONMENT")
    @classmethod
    def normalize_environment(cls, value: str) -> str:
        return value.lower()

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS cannot contain '*'")
        return ",".join(origins)

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()


def ensure_directories() -> None:
    """Create required directories if they do not exist"""
    directories = [
        os.path.dirname(settings.LOG_FILE),
        settings.BACKUP_PATH,
        settings.REPORTS_TEMP_DIR,
    ]

    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


ensure_directories()
