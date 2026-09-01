import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Chatbot API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./rag.db" # Fallback to SQLite async if postgres not available
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Vector DB
    VECTOR_DB_TYPE: str = "memory" # "memory", "qdrant"
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"
    
    # Security
    SECRET_KEY: str = "super-secret-jwt-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
