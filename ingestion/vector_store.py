import os
import json
import uuid
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import Tuple
import config
from utils.logger import get_logger

logger = get_logger(__name__)

# Load embedding model once at module level (expensive to reload each time)
_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


class VectorStore:
    """
    Manages FAISS indexes on disk.
    Each ingested file gets its own index identified by a UUID (index_id).

    Files saved per index:
        {index_id}.faiss          — the FAISS index
        {index_id}_chunks.json    — the original text chunks
        {index_id}_metadata.json  — file type, sql table name, chunk count
    """

    def __init__(self, faiss_dir: str = None):
        self.faiss_dir = faiss_dir or config.FAISS_DIR
        os.makedirs(self.faiss_dir, exist_ok=True)

    # ─────────────────────────────────────────
    # Write
    # ─────────────────────────────────────────

    def save(
        self,
        chunks: list[str],
        metadata: dict,
    ) -> str:
        """
        Embed chunks, build a FAISS index, and persist everything to disk.
        Returns the generated index_id (UUID string).
        """
        if not chunks:
            raise ValueError("Cannot save an empty chunk list.")

        model = get_embedding_model()
        logger.info(f"Embedding {len(chunks)} chunks...")
        embeddings = model.encode(chunks, batch_size=32, show_progress_bar=False)
        vectors = np.array(embeddings).astype("float32")

        index = faiss.IndexFlatL2(vectors.shape[1])
        index.add(vectors)

        index_id = str(uuid.uuid4())

        # Save FAISS index
        faiss.write_index(index, self._faiss_path(index_id))

        # Save chunks
        with open(self._chunks_path(index_id), "w", encoding="utf-8") as f:
            json.dump(chunks, f)

        # Save metadata
        metadata["num_chunks"] = len(chunks)
        with open(self._metadata_path(index_id), "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        logger.info(f"VectorStore saved | index_id={index_id} | chunks={len(chunks)}")
        return index_id

    # ─────────────────────────────────────────
    # Read
    # ─────────────────────────────────────────

    def search(self, index_id: str, query: str, top_k: int = None) -> Tuple[list[str], list[float]]:
        """
        Search the FAISS index for the most similar chunks to `query`.
        Returns (list of chunk texts, list of distances).
        """
        top_k = top_k or config.TOP_K_RESULTS

        if not self._index_exists(index_id):
            raise FileNotFoundError(f"No index found for index_id='{index_id}'")

        model = get_embedding_model()
        index = faiss.read_index(self._faiss_path(index_id))

        with open(self._chunks_path(index_id), "r", encoding="utf-8") as f:
            chunks = json.load(f)

        q_vector = model.encode([query]).astype("float32")
        distances, indices = index.search(q_vector, k=min(top_k, len(chunks)))

        result_chunks = []
        result_distances = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(chunks):
                result_chunks.append(chunks[idx])
                result_distances.append(float(dist))

        logger.debug(
            f"FAISS search done | index_id={index_id} | "
            f"top_k={top_k} | results={len(result_chunks)}"
        )
        return result_chunks, result_distances

    def load_metadata(self, index_id: str) -> dict:
        """Load and return the metadata dict for a given index_id."""
        path = self._metadata_path(index_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Metadata not found for index_id='{index_id}'")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ─────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────

    def _index_exists(self, index_id: str) -> bool:
        return (
            os.path.exists(self._faiss_path(index_id))
            and os.path.exists(self._chunks_path(index_id))
        )

    def _faiss_path(self, index_id: str) -> str:
        return os.path.join(self.faiss_dir, f"{index_id}.faiss")

    def _chunks_path(self, index_id: str) -> str:
        return os.path.join(self.faiss_dir, f"{index_id}_chunks.json")

    def _metadata_path(self, index_id: str) -> str:
        return os.path.join(self.faiss_dir, f"{index_id}_metadata.json")

    def delete(self, index_id: str) -> bool:
        """
        Delete all FAISS files for an index_id.
        Returns True if deleted, False if nothing found.
        """
        files = [
            self._faiss_path(index_id),
            self._chunks_path(index_id),
            self._metadata_path(index_id),
        ]
        deleted_any = False
        for f in files:
            if os.path.exists(f):
                os.remove(f)
                deleted_any = True
        if deleted_any:
            logger.info(f"VectorStore deleted | index_id={index_id}")
        return deleted_any
