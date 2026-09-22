from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env", extra="ignore"
    )

    app_env: str = "development"
    database_url: str
    sql_agent_db_url: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_llm_model: str = "llama3.2:1b"
    ollama_embedding_model: str = "nomic-embed-text"
    jwt_secret_key: str
    jwt_expire_minutes: int = 60
    upload_dir: str = "./storage/uploads"
    cors_origins: str = "http://localhost:5173"


settings = Settings()
