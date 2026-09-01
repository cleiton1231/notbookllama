import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Endpoints do llama-server
    LLAMA_CHAT_URL: str = "http://127.0.0.1:8080"
    LLAMA_EMBED_URL: str = "http://127.0.0.1:8081"
    LLAMA_RERANK_URL: str = "http://127.0.0.1:8082"

    # Diretórios de persistência
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma")
    UPLOAD_DIR: str = str(BASE_DIR / "data" / "uploads")

    # Hiperparâmetros RAG
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 60
    TOP_K_RETRIEVAL: int = 16
    TOP_K_RERANK: int = 5
    MAX_CONTEXT_TOKENS: int = 3500

    # Timeouts (segundos)
    CHAT_TIMEOUT: float = 120.0
    EMBED_TIMEOUT: float = 30.0
    RERANK_TIMEOUT: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def ensure_directories(self) -> None:
        os.makedirs(self.CHROMA_PERSIST_DIR, exist_ok=True)
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)


settings = Settings()
settings.ensure_directories()
