import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = Field(default="Knowvia AI")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="INFO")

    # FastAPI Backend Settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    CORS_ORIGINS: List[str] = Field(default=["*"])

    # LLM API Settings
    LLM_PROVIDER: str = Field(default="groq") # groq, gpt_oss, openai, gemini
    LLM_API_KEY: str = Field(default="your_groq_api_key_here")
    GROQ_API_KEY: Optional[str] = Field(default=None)
    LLM_MODEL: str = Field(default="openai/gpt-oss-20b")
    LLM_BASE_URL: Optional[str] = Field(default=None)
    LLM_TEMPERATURE: float = Field(default=0.0)

    # Local GPT-OSS Settings
    GPT_OSS_MODEL: str = Field(default="openai/gpt-oss-20b")
    GPT_OSS_DEVICE: str = Field(default="auto") # auto, cpu, cuda
    GPT_OSS_MAX_NEW_TOKENS: int = Field(default=512)
    GPT_OSS_TEMPERATURE: float = Field(default=0.0)
    GPT_OSS_QUANTIZATION: Optional[str] = Field(default="4bit")

    # Embedding Settings
    EMBEDDING_PROVIDER: str = Field(default="sentence_transformers")
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = Field(default=384)

    # Vector DB Settings (Qdrant Default)
    VECTOR_DB_TYPE: str = Field(default="qdrant") # qdrant or chroma
    QDRANT_STORAGE_PATH: str = Field(default="./qdrant_data")
    QDRANT_URL: Optional[str] = Field(default=None) # Set for cloud deployment (e.g., https://xyz.cloud.qdrant.io)
    QDRANT_API_KEY: Optional[str] = Field(default=None)
    CHROMA_PERSIST_DIR: str = Field(default="./chroma_data")
    COLLECTION_NAME: str = Field(default="tech_doc_collection")

    # Retrieval & Hybrid Parameters
    TOP_K_DENSE: int = Field(default=10)
    TOP_K_BM25: int = Field(default=10)
    DENSE_WEIGHT: float = Field(default=0.5)
    BM25_WEIGHT: float = Field(default=0.5)
    RERANK_TOP_N: int = Field(default=5)
    RELEVANCE_THRESHOLD: float = Field(default=0.3)

    # Answerability & Evidence Assessment Thresholds
    ANSWERABILITY_STRONG_THRESHOLD: float = Field(default=0.65)
    ANSWERABILITY_PARTIAL_THRESHOLD: float = Field(default=0.20)
    MIN_SUPPORTING_DOCS: int = Field(default=1)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()
