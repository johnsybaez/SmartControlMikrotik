"""Configuración de la aplicación"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env antes de instanciar Settings
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # App Config
    APP_NAME: str = "SmartControl"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = True
    
    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:5174,https://localhost:5173,https://localhost:5174"
    CORS_CREDENTIALS: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite:///./smartbjportal.db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/smartcontrol.log"
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_FORMAT: str = "json"
    
    # MikroTik Default
    MT_HOST: str = "10.80.0.1"
    MT_PORT: int = 8728
    MT_SSH_PORT: int = 2214
    MT_USER: str = "portal"
    MT_PASS: str = "Porta123!!"
    MT_USE_SSL: bool = False
    MT_SSL_VERIFY: bool = False
    MT_TIMEOUT: int = 10
    
    # Address Lists
    LIST_PERMITIDO: str = "INET_PERMITIDO"
    LIST_BLOQUEADO: str = "INET_BLOQUEADO"
    
    # Circuit Breaker
    CIRCUIT_FAILURE_THRESHOLD: int = 3
    CIRCUIT_TIMEOUT_SECONDS: int = 300
    CIRCUIT_HALF_OPEN_MAX_CALLS: int = 1
    
    # Stats
    STATS_COLLECTION_INTERVAL_MINUTES: int = 60
    STATS_RETENTION_DAYS: int = 90
    REPORTS_TEMP_DIR: str = "/tmp/smartcontrol_reports"
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD_SECONDS: int = 60
    
    # Backup
    BACKUP_ENABLED: bool = True
    BACKUP_SCHEDULE: str = "0 2 * * *"
    BACKUP_RETENTION_DAYS: int = 30
    BACKUP_PATH: str = "./backups"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convierte CORS_ORIGINS string a lista"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


# Singleton settings instance
settings = Settings()


# Crear directorios necesarios
def ensure_directories():
    """Crea directorios necesarios si no existen"""
    directories = [
        os.path.dirname(settings.LOG_FILE),
        settings.BACKUP_PATH,
        settings.REPORTS_TEMP_DIR,
    ]
    
    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)


ensure_directories()
