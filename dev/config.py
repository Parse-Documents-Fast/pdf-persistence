from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    HTTP_ADDR: str = "0.0.0.0:8000"
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "pdf_persistence"
    REDIS_HOST: str = "redis-cache"
    REDIS_PORT: int = 6379
    REDIS_TTL: int = 604800  # 7 days in seconds

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
