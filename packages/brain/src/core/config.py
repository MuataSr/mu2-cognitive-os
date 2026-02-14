"""
Configuration for Mu2 Brain API
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Literal, Optional, Union
from pathlib import Path
import os

# Find project root (where .env is located)
# This works whether running from brain package or project root
def find_project_root() -> Path:
    """Find the project root directory by looking for .env file"""
    current = Path.cwd()
    # Look in current directory and parent directories
    for path in [current] + list(current.parents):
        if (path / ".env").exists():
            return path
    # Fallback to script location's parent's parent (brain -> project root)
    return Path(__file__).parent.parent.parent.parent

PROJECT_ROOT = find_project_root()
ENV_FILE = PROJECT_ROOT / ".env"

# Data directories
DATA_DIR = PROJECT_ROOT / "packages" / "brain" / "data"
OPENSTAX_DATA_DIR = DATA_DIR / "openstax"
OPENSTAX_PDFS_DIR = OPENSTAX_DATA_DIR / "pdfs"
OPENSTAX_CHAPTERS_DIR = OPENSTAX_DATA_DIR / "chapters"
OPENSTAX_EMBEDDINGS_DIR = OPENSTAX_DATA_DIR / "embeddings"
OPENSTAX_CHUNKS_DIR = OPENSTAX_DATA_DIR / "chunks"

class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        case_sensitive=False,
        extra="ignore"
    )

    # API Configuration
    api_title: str = "Mu2 Cognitive OS - Brain API"
    api_version: str = "0.1.0"

    # Database - Supports both local Docker and Supabase
    # For local: postgresql://postgres:password@localhost:54322/postgres
    # For Supabase: postgresql://postgres:[PASSWORD]@db.xxxxxxxx.supabase.co:5432/postgres
    database_url: str = "postgresql://postgres:your-super-secret-and-long-postgres-password@localhost:54322/postgres"

    # Supabase Configuration (optional, for direct Supabase client usage)
    # Maps from NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
    supabase_url: Optional[str] = None
    supabase_service_role_key: Optional[str] = None  # Service role key for server-side

    # CORS - Localhost only (NO CLOUD)
    # Add your deployed domains here if needed for production
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
    libretexts_institution_id: Optional[str] = None
    adapt_import_batch_size: int = 10
    adapt_max_import_count: int = 100
    adapt_cache_duration_hours: int = 24

    # Embeddings
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768  # nomic-embed-text produces 768-dim embeddings

    # ============================================================================
    # OpenStax Instructor Resources Configuration
    # ============================================================================
    # OpenStax provides instructor resources including test banks that can be
    # downloaded and imported locally. No API key required.

    # Instructor Resources Base URL
    openstax_instructor_base: str = "https://openstax.org"

    # Available instructor test banks
    openstax_test_banks: list[str] = [
        "biology-2e",           # Biology 2e (matches our loaded content)
        "anatomy-physiology",   # Anatomy & Physiology
        "chemistry-of-life",     # Chemistry of Life (for bio)
        "concepts-biology",      # Concepts of Biology
    ]

    # Import batch size
    question_import_batch_size: int = 50

    # Maximum questions to import per test bank
    question_import_max_count: int = 500

    # Question storage location (relative to data directory)
    question_storage_path: str = "questions"

    # ============================================================================
    # Hybrid LLM Configuration
    # Local Anonymization + Cloud LLM (FERPA Compliant)
    # ============================================================================

    # Enable hybrid mode (local anonymization + cloud LLM)
    llm_hybrid_mode: bool = True

    # Anonymization Settings
    llm_anonymization_enabled: bool = True
    anonymization_method: Literal["pattern", "llm", "hybrid"] = "hybrid"
    anonymization_mask_char: str = "*"
    anonymization_log_enabled: bool = False  # Never log original text (FERPA)

    # Cloud LLM Provider Configuration
    # Supported providers: "minimax", "openai", "anthropic", "google", "custom"
    llm_cloud_provider: str = "minimax"

    # Minimax M2.1 Configuration (Primary Cloud Provider)
    llm_cloud_api_key: Optional[str] = None  # Your Minimax API key
    llm_cloud_base_url: Optional[str] = "https://api.minimax.chat/v1"  # Or "https://api.minimax.io/v1"
    llm_cloud_model: Optional[str] = "M2-her"  # Minimax M2.1 model
    llm_cloud_group_id: Optional[str] = None  # Required for some Minimax APIs

    # Hybrid Routing Settings (string in .env, parsed to list)
    llm_cloud_threshold: float = 0.7  # Complexity threshold (0-1)
    llm_force_cloud_for: Union[str, list[str]] = "generation"  # Always use cloud for these
    llm_local_only_for: Union[str, list[str]] = "embedding"  # Never use cloud for these
    llm_allow_cloud_fallback: bool = True  # Fall back to local if cloud fails

    @field_validator('allowed_origins', 'llm_force_cloud_for', 'llm_local_only_for', mode='before')
    @classmethod
    def parse_list(cls, v):
        """Parse comma-separated string to list"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [item.strip() for item in v.split(',')]
        return v

    def is_supabase(self) -> bool:
        """Check if we're connected to Supabase (not local Docker)"""
        return "supabase.co" in self.database_url.lower()


settings = Settings()

