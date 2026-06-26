"""FastAPI application factory and entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    yield
    # Shutdown
    # Close any resources


def create_app() -> FastAPI:
    app = FastAPI(
        title="E-Commerce AI Studio",
        description="AI-powered image and video generation for e-commerce platforms",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    from app.api.v1.auth import router as auth_router
    from app.api.v1.generate import router as generate_router
    from app.api.v1.assets import router as assets_router
    from app.api.v1.models import router as models_router

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
    app.include_router(generate_router, prefix="/api/v1/generate", tags=["Generation"])
    app.include_router(assets_router, prefix="/api/v1/assets", tags=["Assets"])
    app.include_router(models_router, prefix="/api/v1/models", tags=["Models"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
