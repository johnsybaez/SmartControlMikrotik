"""Script para inicializar la base de datos con datos iniciales"""
from app.db.database import init_db, SessionLocal
from app.db.models import User, Router
from app.core.security import hash_password
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


def seed_database():
    """Seed de datos iniciales"""
    logger.info("Iniciando seed de base de datos...")
    
    # Inicializar DB
    init_db()
    
    db = SessionLocal()
    try:
        # Verificar si ya existe el usuario admin
        admin_exists = db.query(User).filter(User.username == "admin").first()
        
        if not admin_exists:
            # Crear usuario admin
            admin_user = User(
                username="admin",
                password_hash=hash_password("Soporte123"),
                full_name="Administrador",
                email="admin@smartcontrol.local",
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            logger.info("Usuario admin creado: admin/Soporte123")
        else:
            logger.info("Usuario admin ya existe")
        
        # Verificar si ya existe el router default
        router_exists = db.query(Router).filter(Router.host == settings.MT_HOST).first()
        
        if not router_exists:
            # Crear router default desde configuración
            default_router = Router(
                name="Router Principal",
                host=settings.MT_HOST,
                api_port=settings.MT_PORT,
                ssh_port=settings.MT_SSH_PORT,
                username=settings.MT_USER,
                password=settings.MT_PASS,  # TODO: Encriptar en producción
                use_ssl=settings.MT_USE_SSL,
                ssl_verify=settings.MT_SSL_VERIFY,
                timeout=settings.MT_TIMEOUT,
                description="Router MikroTik configurado por defecto",
                status="active"
            )
            db.add(default_router)
            logger.info(f"Router default creado: {settings.MT_HOST}")
        else:
            logger.info("Router default ya existe")
        
        db.commit()
        logger.info("Seed de base de datos completado exitosamente")
        
    except Exception as e:
        logger.error("Error en seed de base de datos", error=str(e))
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
