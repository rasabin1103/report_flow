from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REPORTFLOW_")
    max_file_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    max_rows: int = Field(default=50000, ge=1)
    max_columns: int = Field(default=80, ge=1)
    max_uncompressed_bytes: int = Field(default=80 * 1024 * 1024, ge=1)
    max_pages: int = Field(default=100, ge=1)
    timeout_seconds: int = Field(default=60, ge=0)
    max_concurrent_jobs: int = Field(default=2, ge=1)


class ReportError(ValueError):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status
