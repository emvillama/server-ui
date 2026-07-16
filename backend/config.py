"""
Central place for all configuration. Everything here is loaded from
environment variables (or a .env file in development) so nothing about a
specific machine -- hostnames, ports, model names -- is hardcoded elsewhere
in the codebase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ollama_host: str = "http://localhost:11434"
    default_model: str = "llama3.1:8b"
    db_path: str = "./data/persona_hub.db"
    ollama_timeout: float = 120.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Import this singleton elsewhere: `from backend.config import settings`
settings = Settings()