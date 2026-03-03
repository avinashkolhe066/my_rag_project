import os
from dotenv import load_dotenv

load_dotenv()  # Load from .env file if it exists

# ─────────────────────────────────────────────
# LLM Settings
# ─────────────────────────────────────────────

# Switch between "ollama" or "gemini"
LLM_BACKEND: str = os.getenv("LLM_BACKEND", "ollama")

# Ollama settings
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# Gemini settings
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ─────────────────────────────────────────────
# Embedding Model
# ─────────────────────────────────────────────

EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# ─────────────────────────────────────────────
# Storage Paths
# ─────────────────────────────────────────────

BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
FAISS_DIR: str = os.path.join(BASE_DIR, "faiss_indexes")
DB_PATH: str = os.path.join(BASE_DIR, "products.db")
LOG_DIR: str = os.path.join(BASE_DIR, "logs")

# ─────────────────────────────────────────────
# Chunking Settings
# ─────────────────────────────────────────────

CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", 300))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", 50))

# ─────────────────────────────────────────────
# Search Settings
# ─────────────────────────────────────────────

TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", 10))

# ─────────────────────────────────────────────
# API Settings
# ─────────────────────────────────────────────

API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", 8000))
