from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    GEMINI_API_KEY: str
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/imagematch"


settings = Settings()
