"""FastAPI main application"""
import time
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import init_db
from app.routes import auth, routers, devices, plans, qos, stats, users, audit
from app.core.security import decode_access_token, get_current_user_payload
from app.core.audit import record_audit_event
from app.db.database import SessionLocal

logger = get_logger(__name__)

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Swagger/OpenAPI (JWT Bearer)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API documentation for SmartControl",
        routes=app.routes,
    )

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }

    openapi_schema["security"] = [{"BearerAuth": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(get_current_user_payload)])
async def openapi_json():
    return JSONResponse(app.openapi())


@app.get("/docs", include_in_schema=False, dependencies=[Depends(get_current_user_payload)])
async def swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - Swagger UI",
    )


@app.get("/redoc", include_in_schema=False, dependencies=[Depends(get_current_user_payload)])
async def redoc_ui():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - ReDoc",
    )

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else "unknown"
    )
    
    # Process request
    response = await call_next(request)
    # Audit log for mutating requests with valid JWT
    try:
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]
                payload = decode_access_token(token)
                db = SessionLocal()
                try:
                    record_audit_event(
                        db=db,
                        user_id=payload.get("user_id"),
                        username=payload.get("sub"),
                        action=f"{request.method} {request.url.path}",
                        target=request.url.query or None,
                        result="success" if response.status_code < 400 else "error",
                        extra_data={"status_code": response.status_code}
                    )
                finally:
                    db.close()
    except Exception:
        pass
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2)
    )
    
    return response

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression for faster responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Event handlers
@app.on_event("startup")
async def startup_event():
    """Inicialización al arranque"""
    logger.info("application_starting", 
                app_name=settings.APP_NAME, 
                version=settings.APP_VERSION,
                environment=settings.ENVIRONMENT)
    
    # Inicializar base de datos
    try:
        init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Limpieza al cerrar"""
    logger.info("application_shutting_down")


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# Routers
app.include_router(auth.router, prefix="/api")
app.include_router(
    routers.router,
    prefix="/api",
    dependencies=[Depends(get_current_user_payload)]
)
app.include_router(
    devices.router,
    prefix="/api",
    dependencies=[Depends(get_current_user_payload)]
)
app.include_router(
    plans.router,
    prefix="/api",
    dependencies=[Depends(get_current_user_payload)]
)
app.include_router(
    qos.router,
    prefix="/api",
    dependencies=[Depends(get_current_user_payload)]
)
app.include_router(
    stats.router,
    prefix="/api",
    dependencies=[Depends(get_current_user_payload)]
)
app.include_router(
    users.router,
    prefix="/api",
    dependencies=[Depends(get_current_user_payload)]
)
app.include_router(
    audit.router,
    prefix="/api",
    dependencies=[Depends(get_current_user_payload)]
)


# Root
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
