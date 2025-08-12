
from dataclasses import dataclass
import os

@dataclass
class AppConfig:
    ch_url: str | None
    ch_user: str | None
    ch_pass: str | None
    ch_database: str | None
    ai_provider: str | None
    ai_api_key: str | None

    @property
    def has_clickhouse(self) -> bool:
        return bool(self.ch_url and self.ch_user is not None)

def load_config() -> AppConfig:
    # simple .env loader
    env_path = ".env"
    if os.path.exists(env_path):
        for line in open(env_path):
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line: 
                continue
            k,v = line.split("=",1)
            os.environ.setdefault(k.strip(), v.strip())

    return AppConfig(
        ch_url=os.getenv("CH_URL"),
        ch_user=os.getenv("CH_USER"),
        ch_pass=os.getenv("CH_PASS"),
        ch_database=os.getenv("CH_DATABASE", "default"),
        ai_provider=os.getenv("AI_PROVIDER"),
        ai_api_key=os.getenv("AI_API_KEY"),
    )

