from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(ROOT / '.env', ROOT / 'backend/.env'), extra='ignore')
    database_url: str = 'postgresql+psycopg://tunari:tunari_local@localhost:5432/tunari'
    database_enabled: bool = True
    live_monitoring_enabled: bool = True
    gamc_wms_key: SecretStr = SecretStr('')
    firms_map_key: SecretStr = SecretStr('')
    firms_sources: str = 'MODIS_NRT,VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT'
    bbox: str = '-66.5,-17.6,-65.8,-17.1'
    nrt_interval_hours: int = Field(default=3, ge=3)
    nrt_days: int = Field(default=2, ge=1, le=5)
    nrt_scheduler_enabled: bool = False
    nrt_stale_grace_minutes: int = Field(default=20, ge=5, le=60)
    nrt_source_max_age_hours: int = Field(default=24, ge=6, le=48)
    nrt_http_retries: int = Field(default=2, ge=0, le=2)
    nrt_max_download_mb: int = Field(default=32, ge=1, le=64)
    alerts_evaluation_enabled: bool = False
    data_dir: Path = ROOT / 'data'
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080,http://127.0.0.1:8080'
    notifications_enabled: bool = False
    telegram_bot_token: SecretStr = SecretStr('')
    telegram_chat_id: str = ''
    api_token: SecretStr = SecretStr('')
    min_baseline_years: int = Field(default=5, ge=3)


@lru_cache
def get_settings():
    return Settings()
