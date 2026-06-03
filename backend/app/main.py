import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from app.api import alerts, health, heatmap, hotspots, indicators, meta, reports, trend
from app.config.settings import settings
from app.core.logging import get_logger
from app.services.data_service import data_service
from app.services.alert_service import alert_service
from app.services.indicator_service import indicator_service

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown."""
    logger.info("Starting M10 API...")
    try:
        data_service.load()
        logger.info("Data service ready.")
        indicator_service.recompute()
        logger.info("Indicator service ready.")
        alert_service.recompute()
        logger.info("Alert service ready.")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        raise
    yield
    logger.info("Shutting down M10 API...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers (registered BEFORE static mount so /api/m10/* takes precedence)
app.include_router(health.router, prefix=settings.API_PREFIX, tags=["system"])
app.include_router(meta.router, prefix=settings.API_PREFIX, tags=["system"])
app.include_router(indicators.router, prefix=settings.API_PREFIX, tags=["indicators"])
app.include_router(trend.router, prefix=settings.API_PREFIX, tags=["trend"])
app.include_router(alerts.router, prefix=settings.API_PREFIX, tags=["alerts"])
app.include_router(hotspots.router, prefix=settings.API_PREFIX, tags=["hotspots"])
app.include_router(reports.router, prefix=settings.API_PREFIX, tags=["reports"])
app.include_router(heatmap.router, prefix=settings.API_PREFIX, tags=["heatmap"])


# Mount the prebuilt Next.js static export at "/" so a single command
# (`python run.py`) serves both the API and the SPA on the same port.
# When the build artifacts are missing (e.g. fresh clone, dev mode),
# we just skip the mount and FastAPI returns its default JSON root.
_FRONTEND_OUT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out")
)

# Next.js 16 client-side prefetcher запрашивает RSC payloads вида
#   /<route>/__next.<route>.__PAGE__.txt
# но в static export эти файлы лежат в <route>/__next.<route>/__PAGE__.txt
# (с '/' вместо последней точки). Middleware подменяет path до того, как
# StaticFiles отвечает 404 — тогда файл находится корректно.
_NEXT_PAGE_SUFFIX = ".__PAGE__.txt"


@app.middleware("http")
async def next_prefetch_rewrite(request, call_next):
    path = request.url.path
    # Case A: '<route>/__next.<route>.__PAGE__.txt' → '<route>/__next.<route>/__PAGE__.txt'
    if path.endswith(_NEXT_PAGE_SUFFIX):
        new_path = path[: -len(_NEXT_PAGE_SUFFIX)] + "/__PAGE__.txt"
        request.scope["path"] = new_path
        request.scope["raw_path"] = new_path.encode("ascii")
    # Case B: для root '/' Next.js prefetcher запрашивает '/__next/__PAGE__.txt'
    # вместо '/__next.__PAGE__.txt' (так оно лежит в out/).
    elif path.startswith("/__next/"):
        new_path = "/__next." + path[len("/__next/"):]
        request.scope["path"] = new_path
        request.scope["raw_path"] = new_path.encode("ascii")
    return await call_next(request)


# Заглушка для /_vercel/insights/* (когда-то приходило от @vercel/analytics).
# include_in_schema=False — служебный роут, в Swagger /docs не светим.
@app.get("/_vercel/insights/{rest:path}", include_in_schema=False)
async def _vercel_silent(rest: str):
    return Response(status_code=204)


# Браузеры всегда сами запрашивают /favicon.ico, не зависит от <link rel="icon">.
# Иконку мы намеренно не публикуем — отдаём 204 чтобы не было шумных 404 в access log.
@app.get("/favicon.ico", include_in_schema=False)
async def _favicon_silent():
    return Response(status_code=204)


if os.path.isdir(_FRONTEND_OUT):
    app.mount("/", StaticFiles(directory=_FRONTEND_OUT, html=True), name="frontend")
    logger.info(f"Serving static frontend from {_FRONTEND_OUT}")
else:
    @app.get("/")
    def root():
        """Fallback root when no static build is present (dev / fresh clone)."""
        return {
            "name": settings.APP_NAME,
            "version": settings.VERSION,
            "docs": "/docs",
            "note": "frontend/out not found — run `npm run build` in frontend/ to enable SPA serving",
        }
