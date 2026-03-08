"""FastAPI main application."""
import time

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.audit import record_audit_event
from app.core.config import settings
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.core.security import decode_access_token, get_current_user_payload
from app.db.database import SessionLocal, init_db
from app.routes import audit, auth, devices, plans, qos, routers, stats, users

logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    lambda request, exc: JSONResponse(status_code=429, content={"detail": "Demasiadas solicitudes"}),
)
app.add_middleware(SlowAPIMiddleware)

# Security middlewares
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts_list or ["localhost", "127.0.0.1"],
)
if settings.FORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


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


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    if settings.ENABLE_SECURITY_HEADERS:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    logger.info(
        "http_request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else "unknown",
    )

    response = await call_next(request)

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
                        extra_data={"status_code": response.status_code},
                    )
                finally:
                    db.close()
    except Exception as exc:
        logger.warning("audit_capture_failed", path=request.url.path, error=str(exc))

    process_time = time.time() - start_time
    logger.info(
        "http_request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2),
    )

    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


@app.on_event("startup")
async def startup_event():
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )
    try:
        init_db()
        logger.info("database_initialized")
    except Exception as exc:
        logger.error("database_init_failed", error=str(exc))
        raise


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("application_shutting_down")


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


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


app.include_router(auth.router, prefix="/api")
app.include_router(routers.router, prefix="/api", dependencies=[Depends(get_current_user_payload)])
app.include_router(devices.router, prefix="/api", dependencies=[Depends(get_current_user_payload)])
app.include_router(plans.router, prefix="/api", dependencies=[Depends(get_current_user_payload)])
app.include_router(qos.router, prefix="/api", dependencies=[Depends(get_current_user_payload)])
app.include_router(stats.router, prefix="/api", dependencies=[Depends(get_current_user_payload)])
app.include_router(users.router, prefix="/api", dependencies=[Depends(get_current_user_payload)])
app.include_router(audit.router, prefix="/api", dependencies=[Depends(get_current_user_payload)])


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
