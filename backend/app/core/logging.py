"""Configuración de logging estructurado"""
import logging
import structlog
from pathlib import Path
from logging.handlers import RotatingFileHandler
import sys
from .config import settings


def configure_logging():
    """Configura logging estructurado con structlog"""
    
    # Asegurar que el directorio de logs existe
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configurar logging estándar
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler con rotación
            RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=settings.LOG_MAX_BYTES,
                backupCount=settings.LOG_BACKUP_COUNT,
            ),
        ],
    )
    
    # Configurar structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Procesador final según formato
    if settings.LOG_FORMAT == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Obtiene un logger estructurado"""
    return structlog.get_logger(name)


# Configurar al importar
configure_logging()
