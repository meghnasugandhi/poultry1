from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Poultry ERP AI Assistant"
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "sqlite+aiosqlite:///./poultry_erp.db"

    OPENAI_API_KEY: str = ""
    OCR_SERVICE_URL: str = "http://localhost:8001"
    OCR_SPACE_API_KEY: str = ""  # optional: set to use OCR.Space cloud OCR (free tier available)

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10


settings = Settings()
