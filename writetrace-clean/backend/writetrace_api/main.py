from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import create_router
from .settings import Settings, load_settings
from .storage import JsonWriteTraceStore


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or load_settings()
    app = FastAPI(title=active_settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.cors_origins),
        allow_credentials="*" not in active_settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = JsonWriteTraceStore(active_settings.data_file)
    app.include_router(create_router(store))
    return app


app = create_app()
