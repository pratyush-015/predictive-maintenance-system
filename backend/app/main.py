from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import alerts, auth, devices, metrics, predictions, ws
from app.core.config import settings
from app.core.logging_config import configure_logging, logger
from app.db.database import init_db
from app.ml_runtime.model_loader import registry


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    logger.info("Starting %s [%s]", settings.PROJECT_NAME, settings.ENVIRONMENT)
    init_db()
    registry.reload()
    if not registry.models:
        logger.warning(
            "No trained ML models found in %s — predictions will be inert until you run "
            "`python ml/train_baseline.py` (and optionally ml/train_deep.py).",
            registry.model_dir,
        )
    yield
    logger.info("Shutting down %s", settings.PROJECT_NAME)


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Real-time monitoring, anomaly detection, and predictive maintenance for laptops, "
    "servers, and IoT devices.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(metrics.router, prefix=settings.API_V1_PREFIX)
app.include_router(predictions.router, prefix=settings.API_V1_PREFIX)
app.include_router(alerts.router, prefix=settings.API_V1_PREFIX)
app.include_router(devices.router, prefix=settings.API_V1_PREFIX)
app.include_router(ws.router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["meta"])
def health():
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "models_loaded": list(registry.models.keys()),
    }


@app.get("/", tags=["meta"])
def root():
    return {
        "name": settings.PROJECT_NAME,
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.API_V1_PREFIX,
    }
