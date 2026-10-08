from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: SecretStr = SecretStr("postgresql+psycopg://localhost/documind")
    document_storage_dir: Path = ROOT / ".runtime" / "uploads"
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)
    max_pdf_pages: int = Field(default=50, gt=0)
    max_image_pixels: int = Field(default=25_000_000, gt=0)
    ocr_auto_process: bool = True
    ocr_pdf_dpi: int = Field(default=144, ge=72, le=300)
    ocr_cpu_threads: int = Field(default=2, ge=1, le=32)
    ocr_queue_capacity: int = Field(default=8, ge=1, le=100)
    ocr_cache_dir: Path = ROOT / ".runtime" / "paddlex"
    classification_model_path: Path = ROOT / ".runtime" / "classification" / "baseline.joblib"

    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: SecretStr) -> SecretStr:
        if make_url(value.get_secret_value()).drivername != "postgresql+psycopg":
            raise ValueError("DATABASE_URL must use postgresql+psycopg")
        return value

    @field_validator("document_storage_dir", "ocr_cache_dir", "classification_model_path")
    @classmethod
    def resolve_storage(cls, value: Path) -> Path:
        return value if value.is_absolute() else ROOT / value
