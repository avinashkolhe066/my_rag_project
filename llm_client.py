import requests
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class LLMClient:
    """
    A unified client for interacting with LLM backends.
    Supports 'ollama' (local) and 'gemini' (Google API).
    Backend is read from config but can be overridden at init.
    """

    def __init__(self, backend: str = None, api_key: str = None, model: str = None):
        self.backend = (backend or config.LLM_BACKEND).lower()

        if self.backend == "gemini":
            self.api_key = api_key or config.GEMINI_API_KEY
            if not self.api_key:
                raise ValueError(
                    "Gemini API key is required. Set GEMINI_API_KEY in your .env file."
                )
            self.model = model or config.GEMINI_MODEL
            self.url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"{self.model}:generateContent?key={self.api_key}"
            )
            logger.info(f"LLMClient initialized | backend=gemini | model={self.model}")

        elif self.backend == "ollama":
            self.model = model or config.OLLAMA_MODEL
            self.url = f"{config.OLLAMA_URL.rstrip('/')}/api/generate"
            logger.info(f"LLMClient initialized | backend=ollama | model={self.model}")

        else:
            raise ValueError(
                f"Unknown backend '{self.backend}'. Choose 'ollama' or 'gemini'."
            )

    def generate(self, prompt: str) -> str:
        """
        Send a prompt to the configured LLM and return the response text.
        Raises an exception with a clear message on failure.
        """
        logger.debug(f"Sending prompt to {self.backend} (length={len(prompt)} chars)")

        try:
            if self.backend == "gemini":
                return self._call_gemini(prompt)
            else:
                return self._call_ollama(prompt)
        except Exception as e:
            logger.error(f"LLM generate failed: {e}")
            raise

    # ─────────────────────────────────────────
    # Private Methods
    # ─────────────────────────────────────────

    def _call_gemini(self, prompt: str) -> str:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]
        }
        response = requests.post(self.url, json=payload, timeout=60)

        if response.status_code != 200:
            raise ConnectionError(
                f"Gemini API error {response.status_code}: {response.text}"
            )

        data = response.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            logger.debug("Gemini response received successfully")
            return text
        except (KeyError, IndexError) as e:
            raise ValueError(f"Unexpected Gemini response structure: {data}") from e

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        response = requests.post(self.url, json=payload, timeout=120)

        if response.status_code != 200:
            raise ConnectionError(
                f"Ollama API error {response.status_code}: {response.text}"
            )

        data = response.json()
        text = data.get("response", "")
        logger.debug("Ollama response received successfully")
        return text
