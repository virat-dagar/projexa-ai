import os
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_FILE = BACKEND_DIR / "data" / "writetrace-store.json"
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5500",
    "http://localhost:5500",
)


@dataclass(frozen=True)
class Settings:
    app_name: str
    data_file: Path
    cors_origins: tuple[str, ...]


def _csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


def _resolve_data_file(raw_value: str | None) -> Path:
    if raw_value:
        path = Path(raw_value).expanduser()
        return path if path.is_absolute() else BACKEND_DIR / path

    if os.getenv("VERCEL"):
        return Path("/tmp/writetrace-store.json")

    return DEFAULT_DATA_FILE


def load_settings() -> Settings:
    return Settings(
        app_name=os.getenv("WRITETRACE_APP_NAME", "WriteTrace API"),
        data_file=_resolve_data_file(os.getenv("WRITETRACE_DATA_FILE")),
        cors_origins=_csv(os.getenv("WRITETRACE_CORS_ORIGINS")) or DEFAULT_CORS_ORIGINS,
    )
