import uuid
import json
import os
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

WORKSPACE_FILE = "workspaces.json"


class WorkspaceManager:
    """
    Manages workspaces. Each workspace:
      - Has a unique workspace_id
      - Has a name (user-defined)
      - Holds exactly one uploaded file (one index_id)
      - Has its own isolated chat history via ConversationMemory
      - Can be deleted entirely (workspace + file + history)

    Workspaces are persisted to workspaces.json so they survive server restarts.
    """

    def __init__(self, storage_path: str = WORKSPACE_FILE):
        self.storage_path = storage_path
        self._store: dict[str, dict] = {}
        self._load()

    # ─────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────

    def create(self, name: str) -> dict:
        """Create a new empty workspace. Returns the workspace dict."""
        workspace_id = str(uuid.uuid4())
        workspace = {
            "workspace_id": workspace_id,
            "name": name,
            "index_id": None,
            "file_name": None,
            "file_type": None,
            "sql_table": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self._store[workspace_id] = workspace
        self._save()
        logger.info(f"Workspace created | id={workspace_id} | name={name}")
        return workspace

    def get(self, workspace_id: str) -> dict | None:
        """Return workspace dict or None if not found."""
        return self._store.get(workspace_id)

    def list_all(self) -> list[dict]:
        """Return all workspaces as a list."""
        return list(self._store.values())

    def attach_file(
        self,
        workspace_id: str,
        index_id: str,
        file_name: str,
        file_type: str,
        sql_table: str | None,
    ) -> dict:
        """
        Attach an ingested file to a workspace.
        Replaces any previously attached file.
        """
        workspace = self._store.get(workspace_id)
        if not workspace:
            raise KeyError(f"Workspace '{workspace_id}' not found.")

        workspace["index_id"] = index_id
        workspace["file_name"] = file_name
        workspace["file_type"] = file_type
        workspace["sql_table"] = sql_table
        workspace["updated_at"] = datetime.utcnow().isoformat()

        self._save()
        logger.info(
            f"File attached to workspace | workspace_id={workspace_id} | "
            f"index_id={index_id} | file={file_name}"
        )
        return workspace

    def delete(self, workspace_id: str) -> bool:
        """Delete a workspace. Returns True if deleted, False if not found."""
        if workspace_id not in self._store:
            return False
        del self._store[workspace_id]
        self._save()
        logger.info(f"Workspace deleted | id={workspace_id}")
        return True

    def exists(self, workspace_id: str) -> bool:
        return workspace_id in self._store

    # ─────────────────────────────────────────
    # Persistence
    # ─────────────────────────────────────────

    def _save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self._store, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save workspaces: {e}")

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self._store = json.load(f)
                logger.info(f"Loaded {len(self._store)} workspace(s) from disk")
            except Exception as e:
                logger.error(f"Failed to load workspaces: {e}")
                self._store = {}
        else:
            self._store = {}
