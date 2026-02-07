"""
Configuration for Mu2 Brain API
"""

from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    """Application settings"""

    # API Configuration
    api_title: str = "Mu2 Cognitive OS - Brain API"
    api_version: str = "0.1.0"

    # Database
    database_url: str = "postgresql://supabase_admin@localhost:54322/postgres"

    # CORS - Localhost only (NO CLOUD)
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # LLM Configuration (for future use)
    llm_provider: Literal["openai", "ollama", "local"] = "ollama"
    llm_model: str = "gemma3:1b"  # Small model for old rigs
    llm_base_url: str = "http://localhost:11434"

    # LibreTexts ADAPT API
    libretexts_api_url: str = "https://adapt.libretexts.org/api"
    libretexts_api_key: str = ""

    # Embeddings
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768  # nomic-embed-text produces 768-dim embeddings

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
