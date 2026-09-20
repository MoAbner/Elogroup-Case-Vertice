from dataclasses import dataclass
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]

def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_env(ROOT / ".env")
_load_env(ROOT / ".env.local")

@dataclass(frozen=True)
class Settings:
    api_key: str = os.getenv("ELOGROUP_API_KEY", "")
    api_base_url: str = os.getenv("ELOGROUP_API_BASE_URL", "https://chat.eloagents.click/api/v1/sandbox").rstrip("/")
    api_model: str = os.getenv("ELOGROUP_API_MODEL", "")
    api_timeout: int = int(os.getenv("ELOGROUP_API_TIMEOUT_SECONDS", "25"))
    api_max_tokens: int = int(os.getenv("ELOGROUP_API_MAX_TOKENS", "420"))
    host: str = os.getenv("APP_HOST", "127.0.0.1")
    port: int = int(os.getenv("APP_PORT", "8080"))
    db_path: Path = (ROOT / os.getenv("APP_DB_PATH", "app/data/prototipo.db")).resolve()

settings = Settings()

