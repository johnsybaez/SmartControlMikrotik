"""Script para ejecutar migraciones (crear tablas)"""
from app.db.database import init_db
from app.core.logging import get_logger

logger = get_logger(__name__)


def run_migrations():
    """Ejecuta migraciones (crea tablas)"""
    logger.info("Ejecutando migraciones...")
    try:
        init_db()
        logger.info("Migraciones completadas exitosamente")
    except Exception as e:
        logger.error("Error en migraciones", error=str(e))
        raise


if __name__ == "__main__":
    run_migrations()
