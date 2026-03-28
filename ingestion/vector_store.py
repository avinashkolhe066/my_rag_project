import os
import json
import uuid
import math
import numpy as np
import faiss
from collections import defaultdict
from sentence_transformers import SentenceTransformer
from typing import Tuple
import config
from utils.logger import get_logger

logger = get_logger(__name__)

_embedding_model = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-10, norms)
    return vectors / norms


# ─────────────────────────────────────────────────────────────────────────────
# BM25 — pure Python, no extra dependency
# BM25 is a keyword ranking algorithm (improved TF-IDF).
# It scores chunks by how many query terms they contain, weighted by:
#   - Term Frequency (how often term appears in chunk)
#   - Inverse Document Frequency (how rare term is across all chunks)
#   - Document length normalization (penalizes very long chunks)
# ─────────────────────────────────────────────────────────────────────────────

class BM25:
    """
    BM25Okapi implementation — no external dependencies.
    k1=1.5 controls term frequency saturation.
    b=0.75 controls length normalization.
    """

    def __init__(self, chunks: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b  = b
        self.corpus = [self._tokenize(c) for c in chunks]
        self.n = len(self.corpus)
        self.avgdl = sum(len(d) for d in self.corpus) / max(self.n, 1)

        # Build IDF: log((N - df + 0.5) / (df + 0.5) + 1)
        df = defaultdict(int)
        for doc in self.corpus:
            for term in set(doc):
                df[term] += 1

        self.idf = {}
        for term, freq in df.items():
            self.idf[term] = math.log((self.n - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query: str, top_k: int) -> list[tuple[int, float]]:
        """Return list of (chunk_index, bm25_score) sorted descending."""
        terms = self._tokenize(query)
        scores = []

        for i, doc in enumerate(self.corpus):
            dl   = len(doc)
            score = 0.0
            tf_map = defaultdict(int)
            for t in doc:
                tf_map[t] += 1

            for term in terms:
                if term not in self.idf:
                    continue
                tf   = tf_map.get(term, 0)
                idf  = self.idf[term]
                num  = tf * (self.k1 + 1)
                den  = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                score += idf * num / den

            scores.append((i, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase + split on non-alphanumeric characters."""
        import re
        return re.findall(r"[a-zA-Z0-9]+", text.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Reciprocal Rank Fusion
# Merges rankings from FAISS and BM25 into one unified ranking.
# Formula: RRF_score(doc) = sum(1 / (k + rank_i))
# k=60 is the standard constant — dampens the impact of very high ranks.
# ─────────────────────────────────────────────────────────────────────────────

def reciprocal_rank_fusion(
    faiss_results: list[tuple[int, float]],
    bm25_results:  list[tuple[int, float]],
    k: int = 60,
    faiss_weight: float = 0.6,
    bm25_weight:  float = 0.4,
) -> list[tuple[int, float]]:
    """
    Fuse FAISS and BM25 rankings using RRF.
    Returns sorted list of (chunk_index, rrf_score).

    Weights: FAISS=0.6 (semantic understanding), BM25=0.4 (keyword precision)
    Tuned for document Q&A where semantic understanding matters more.
    """
    rrf_scores = defaultdict(float)

    for rank, (idx, _) in enumerate(faiss_results):
        rrf_scores[idx] += faiss_weight * (1.0 / (k + rank + 1))

    for rank, (idx, _) in enumerate(bm25_results):
        rrf_scores[idx] += bm25_weight * (1.0 / (k + rank + 1))

    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return fused


# ─────────────────────────────────────────────────────────────────────────────
# VectorStore — Hybrid FAISS + BM25
# ─────────────────────────────────────────────────────────────────────────────

class VectorStore:
    """
    Hybrid search: FAISS (semantic) + BM25 (keyword) fused with RRF.

    Why hybrid beats either alone:
    - FAISS finds semantically similar content even with different wording
    - BM25 finds exact keyword matches FAISS might miss (names, codes, jargon)
    - RRF fusion gives you the best of both worlds
    """

    def __init__(self, faiss_dir: str = None):
        self.faiss_dir = faiss_dir or config.FAISS_DIR
        os.makedirs(self.faiss_dir, exist_ok=True)

    # ─────────────────────────────────────────
    # Write
    # ─────────────────────────────────────────

    def save(self, chunks: list[str], metadata: dict) -> str:
        if not chunks:
            raise ValueError("Cannot save an empty chunk list.")

        model = get_embedding_model()
        logger.info(f"Embedding {len(chunks)} chunks...")

        embeddings = model.encode(
            chunks, batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        vectors = np.array(embeddings).astype("float32")
        vectors = _normalize(vectors)

        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)

        index_id = str(uuid.uuid4())
        faiss.write_index(index, self._faiss_path(index_id))

        with open(self._chunks_path(index_id), "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False)

        metadata["num_chunks"] = len(chunks)
        with open(self._metadata_path(index_id), "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        # Save page map if this was a PDF (populated by file_handler._parse_pdf)
        try:
            from ingestion.file_handler import get_last_page_map
            page_map = get_last_page_map()
            if page_map:
                with open(self._pagemap_path(index_id), "w", encoding="utf-8") as f:
                    json.dump(page_map, f)
                logger.info(f"Page map saved | index_id={index_id} | pages={len(set(page_map.values()))}")
        except Exception as e:
            logger.debug(f"No page map to save: {e}")

        logger.info(f"VectorStore saved | index_id={index_id} | chunks={len(chunks)}")
        return index_id

    # ─────────────────────────────────────────
    # Hybrid Search
    # ─────────────────────────────────────────

    def search(
        self,
        index_id: str,
        query: str,
        top_k: int = None,
    ) -> Tuple[list[str], list[float]]:
        """
        Hybrid search: FAISS + BM25 fused with Reciprocal Rank Fusion.

        Steps:
        1. FAISS cosine similarity search → top candidates
        2. BM25 keyword search → top candidates
        3. RRF fusion → unified ranking
        4. Return top_k chunks with normalized scores

        This gives significantly better retrieval than either method alone,
        especially for queries mixing natural language with specific terms.
        """
        top_k = top_k or config.TOP_K_RESULTS

        if not self._index_exists(index_id):
            raise FileNotFoundError(f"No index found for index_id='{index_id}'")

        with open(self._chunks_path(index_id), "r", encoding="utf-8") as f:
            chunks = json.load(f)

        if not chunks:
            return [], []

        # Fetch more candidates than needed — RRF will re-rank and trim
        fetch_k = min(top_k * 3, len(chunks))

        # ── Step 1: FAISS semantic search ─────────────────────────────────
        model = get_embedding_model()
        index = faiss.read_index(self._faiss_path(index_id))
        q_vec = model.encode([query], normalize_embeddings=True).astype("float32")
        q_vec = _normalize(q_vec)

        faiss_scores, faiss_indices = index.search(q_vec, k=fetch_k)
        faiss_results = [
            (int(idx), float(score))
            for idx, score in zip(faiss_indices[0], faiss_scores[0])
            if idx < len(chunks)
        ]

        # ── Step 2: BM25 keyword search ───────────────────────────────────
        bm25 = BM25(chunks)
        bm25_results = bm25.score(query, top_k=fetch_k)
        # Filter out zero-score BM25 results (query terms not found at all)
        bm25_results = [(i, s) for i, s in bm25_results if s > 0]

        # ── Step 3: RRF fusion ────────────────────────────────────────────
        if bm25_results:
            # Both methods returned results — fuse them
            fused = reciprocal_rank_fusion(faiss_results, bm25_results)
            logger.debug(
                f"Hybrid search | FAISS={len(faiss_results)} | "
                f"BM25={len(bm25_results)} | fused={len(fused)}"
            )
        else:
            # BM25 found nothing (query terms absent) — fall back to FAISS only
            fused = [(idx, score) for idx, score in faiss_results]
            logger.debug(f"Hybrid search | BM25 no matches, using FAISS only")

        # ── Step 4: Apply minimum FAISS score filter + return top_k ──────
        # Build a lookup of FAISS scores for threshold filtering
        faiss_score_map = {idx: score for idx, score in faiss_results}
        MIN_FAISS_SCORE = 0.15  # lowered slightly since BM25 can compensate

        result_chunks = []
        result_scores = []

        for idx, rrf_score in fused[:top_k]:
            faiss_score = faiss_score_map.get(idx, 0.0)
            # Include if either: good semantic similarity OR strong BM25 match
            if faiss_score >= MIN_FAISS_SCORE or rrf_score > 0.005:
                result_chunks.append(chunks[idx])
                result_scores.append(round(rrf_score, 6))

        if result_scores:
            logger.info(
                f"Hybrid search done | index_id={index_id[:8]}... | "
                f"returned={len(result_chunks)} | top_rrf={result_scores[0]:.4f}"
            )
        else:
            logger.warning(f"Hybrid search | no results above threshold")

        return result_chunks, result_scores

    def get_chunk_pages(self, index_id: str, chunks: list[str]) -> list[int | None]:
        """
        Given a list of chunk texts, return their page numbers.
        Returns list of page numbers (or None if not a PDF / page unknown).
        """
        pagemap_path = self._pagemap_path(index_id)
        if not os.path.exists(pagemap_path):
            return [None] * len(chunks)

        with open(pagemap_path, "r") as f:
            page_map = json.load(f)  # {str(chunk_index): page_number}

        # Load chunks to find indices
        try:
            with open(self._chunks_path(index_id), "r", encoding="utf-8") as f:
                all_chunks = json.load(f)
        except Exception:
            return [None] * len(chunks)

        # Build reverse lookup: chunk_text -> page_number
        chunk_to_page = {}
        for i, chunk_text in enumerate(all_chunks):
            page_num = page_map.get(str(i))
            if page_num:
                chunk_to_page[chunk_text] = page_num

        return [chunk_to_page.get(c) for c in chunks]

    def load_metadata(self, index_id: str) -> dict:
        path = self._metadata_path(index_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Metadata not found for index_id='{index_id}'")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ─────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────

    def _index_exists(self, index_id: str) -> bool:
        return (
            os.path.exists(self._faiss_path(index_id))
            and os.path.exists(self._chunks_path(index_id))
        )

    def _faiss_path(self, index_id):    return os.path.join(self.faiss_dir, f"{index_id}.faiss")
    def _chunks_path(self, index_id):   return os.path.join(self.faiss_dir, f"{index_id}_chunks.json")
    def _metadata_path(self, index_id): return os.path.join(self.faiss_dir, f"{index_id}_metadata.json")
    def _pagemap_path(self, index_id):  return os.path.join(self.faiss_dir, f"{index_id}_pagemap.json")

    def delete(self, index_id: str) -> bool:
        files = [
            self._faiss_path(index_id),
            self._chunks_path(index_id),
            self._metadata_path(index_id),
            self._pagemap_path(index_id),
        ]
        deleted = False
        for f in files:
            if os.path.exists(f):
                os.remove(f)
                deleted = True
        if deleted:
            logger.info(f"VectorStore deleted | index_id={index_id}")
        return deleted