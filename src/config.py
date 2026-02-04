"""Configuration management using Pydantic Settings."""
import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration with validation and environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # OpenAI Configuration (for embeddings and LLM via Azure)
    openai_api_key: str = Field(..., description="Azure API key")
    openai_api_endpoint: Optional[str] = Field(default=None, description="Azure OpenAI endpoint")
    openai_api_version: Optional[str] = Field(default=None, description="Azure OpenAI API version")
    
    # Model Configuration
    llm_model: str = Field(default="gpt-4.1-mini", description="Azure deployment name")
    embedding_model: str = Field(
        default="text-embedding-3-large",
        description="Azure deployment name"
    )
    
    # ChromaDB Configuration
    chroma_persist_directory: str = Field(
        default="./chroma_data",
        description="Directory for ChromaDB persistence"
    )
    
    # Chunking Configuration
    chunk_size: int = Field(default=1000, description="Character chunk size for text splitting")
    chunk_overlap: int = Field(default=200, description="Character overlap between chunks")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    
    @property
    def is_azure(self) -> bool:
        """Check if using Azure OpenAI."""
        return self.openai_api_endpoint is not None
    
    @validator("chroma_persist_directory")
    def create_persist_directory(cls, v: str) -> str:
        """Ensure the persistence directory exists."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.absolute())
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate and set the logging level."""
        v = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, v),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return v


# Global config instance
config: Optional[Config] = None


def get_config() -> Config:
    """Get or create the global config instance."""
    global config
    if config is None:
        config = Config()
    return config
