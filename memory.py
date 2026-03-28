import json
import os
from collections import defaultdict
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_HISTORY = 20   # max exchanges per conversation (1 exchange = 1 Q + 1 A)


class ConversationMemory:
    """
    Stores conversation history per index_id.
    Persisted to a JSON file on disk so history survives server restarts and page refreshes.
    """

    def __init__(self, persist_path: str = "conversation_history.json"):
        self.persist_path = persist_path
        # key: index_id → list of {"role": "user"|"assistant", "content": "..."}
        self._store: dict[str, list[dict]] = defaultdict(list)
        self._load()

    # ─────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────

    def add(self, index_id: str, question: str, answer: str) -> None:
        """Add a user question and assistant answer, then persist."""
        history = self._store[index_id]
        history.append({"role": "user",      "content": question})
        history.append({"role": "assistant", "content": answer})

        # Trim to last MAX_HISTORY exchanges
        max_entries = MAX_HISTORY * 2
        if len(history) > max_entries:
            self._store[index_id] = history[-max_entries:]

        self._save()
        logger.debug(
            f"Memory updated | index_id={index_id} | "
            f"total_exchanges={len(self._store[index_id]) // 2}"
        )

    def get(self, index_id: str) -> list[dict]:
        """Return the full conversation history for a given index_id."""
        return self._store[index_id].copy()

    def get_all(self, index_id: str) -> list[dict]:
        """Alias for get() — returns full history list."""
        return self._store[index_id].copy()

    def format_for_prompt(self, index_id: str, max_turns: int = 6) -> str:
        """
        Format recent conversation history for LLM prompt injection.
        Only uses last max_turns exchanges to keep context tight and relevant.
        """
        history = self._store[index_id]
        if not history:
            return ""

        # Take only recent history — last max_turns * 2 messages
        recent = history[-(max_turns * 2):]

        lines = ["=== CONVERSATION HISTORY (most recent first) ==="]
        # Reverse to show most recent at bottom (LLMs attend more to recent context)
        pairs = []
        for i in range(0, len(recent) - 1, 2):
            if i + 1 < len(recent):
                user_msg = recent[i]["content"]
                asst_msg = recent[i + 1]["content"]
                # Truncate very long assistant answers to keep prompt size manageable
                if len(asst_msg) > 500:
                    asst_msg = asst_msg[:500] + "... [truncated]"
                pairs.append((user_msg, asst_msg))

        for user_msg, asst_msg in pairs:
            lines.append(f"User: {user_msg}")
            lines.append(f"Assistant: {asst_msg}")
            lines.append("")  # blank line between turns

        lines.append("=== END OF HISTORY ===")
        return "\n".join(lines)

    def clear(self, index_id: str) -> None:
        """Clear history for a specific index_id and persist."""
        if index_id in self._store:
            del self._store[index_id]
            self._save()
            logger.info(f"Memory cleared | index_id={index_id}")

    def clear_all(self) -> None:
        """Clear all conversation history and persist."""
        self._store.clear()
        self._save()
        logger.info("All conversation memory cleared")

    def get_exchange_count(self, index_id: str) -> int:
        """Return number of Q&A exchanges for this index_id."""
        return len(self._store[index_id]) // 2

    # ─────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────

    def _save(self) -> None:
        """Write current memory to disk as JSON."""
        try:
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(dict(self._store), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to persist memory: {e}")

    def _load(self) -> None:
        """Load persisted memory from disk on startup."""
        if not os.path.exists(self.persist_path):
            logger.info("No persisted memory found — starting fresh.")
            return
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for index_id, history in data.items():
                self._store[index_id] = history
            total = sum(len(v) // 2 for v in self._store.values())
            logger.info(f"Loaded persisted memory | conversations={len(self._store)} | total_exchanges={total}")
        except Exception as e:
            logger.warning(f"Failed to load persisted memory (starting fresh): {e}")