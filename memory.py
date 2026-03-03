from collections import defaultdict
from utils.logger import get_logger

logger = get_logger(__name__)

# Maximum number of previous exchanges to keep per index_id
# (1 exchange = 1 user question + 1 assistant answer)
MAX_HISTORY = 10


class ConversationMemory:
    """
    Stores conversation history per index_id in memory.
    History is lost when the server restarts (by design).

    Each entry in history is a dict:
        {"role": "user" or "assistant", "content": "..."}
    """

    def __init__(self):
        # key: index_id → value: list of {"role": ..., "content": ...}
        self._store: dict[str, list[dict]] = defaultdict(list)

    def add(self, index_id: str, question: str, answer: str) -> None:
        """Add a user question and assistant answer to the history."""
        history = self._store[index_id]
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})

        # Trim to keep only last MAX_HISTORY exchanges (each exchange = 2 entries)
        max_entries = MAX_HISTORY * 2
        if len(history) > max_entries:
            self._store[index_id] = history[-max_entries:]

        logger.debug(
            f"Memory updated | index_id={index_id} | "
            f"total_exchanges={len(self._store[index_id]) // 2}"
        )

    def get(self, index_id: str) -> list[dict]:
        """Return the full conversation history for a given index_id."""
        return self._store[index_id].copy()

    def format_for_prompt(self, index_id: str) -> str:
        """
        Format history as a readable string to inject into LLM prompts.
        Returns empty string if no history exists.
        """
        history = self._store[index_id]
        if not history:
            return ""

        lines = ["Previous conversation:"]
        for entry in history:
            role = "User" if entry["role"] == "user" else "Assistant"
            lines.append(f"{role}: {entry['content']}")

        return "\n".join(lines)

    def clear(self, index_id: str) -> None:
        """Clear history for a specific index_id."""
        if index_id in self._store:
            del self._store[index_id]
            logger.info(f"Memory cleared | index_id={index_id}")

    def clear_all(self) -> None:
        """Clear all conversation history."""
        self._store.clear()
        logger.info("All conversation memory cleared")

    def get_exchange_count(self, index_id: str) -> int:
        """Return how many question/answer exchanges exist for this index_id."""
        return len(self._store[index_id]) // 2
