import re
import json
import pandas as pd
import PyPDF2
from io import BytesIO
from typing import Tuple, Optional
from utils.logger import get_logger
import config

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".json", ".pdf", ".txt"}


def get_extension(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def parse_file(
    content: bytes, filename: str
) -> Tuple[list[str], Optional[pd.DataFrame], str]:
    ext = get_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed types: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    logger.info(f"Parsing file | name={filename} | ext={ext}")

    if ext == ".csv":   return _parse_csv(content)
    elif ext == ".json": return _parse_json(content)
    elif ext == ".pdf":  return _parse_pdf(content)
    elif ext == ".txt":  return _parse_txt(content)


# ─────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────

def _parse_csv(content: bytes):
    df = pd.read_csv(BytesIO(content))
    chunks = _dataframe_to_chunks(df)
    logger.debug(f"CSV parsed | rows={len(df)} | chunks={len(chunks)}")
    return chunks, df, "csv"


def _parse_json(content: bytes):
    data = json.loads(content)
    if isinstance(data, list) and all(isinstance(i, dict) for i in data):
        df = pd.DataFrame(data)
        chunks = _dataframe_to_chunks(df)
        logger.debug(f"JSON array parsed | rows={len(df)} | chunks={len(chunks)}")
        return chunks, df, "json_array"
    text = json.dumps(data, indent=2)
    chunks = split_text_smart(text)
    return chunks, None, "json"


def _parse_pdf(content: bytes):
    pdf_reader = PyPDF2.PdfReader(BytesIO(content))
    total_pages = len(pdf_reader.pages)

    # Parse each page separately to track page numbers
    page_chunks = []   # list of (chunk_text, page_number)
    pages_text  = []

    for i, page in enumerate(pdf_reader.pages):
        page_num  = i + 1
        page_text = page.extract_text()
        if page_text and page_text.strip():
            cleaned = _clean_pdf_text(page_text)
            pages_text.append(cleaned)
            # Split this page into chunks — each chunk tagged with page number
            page_splits = split_text_smart(cleaned)
            for chunk in page_splits:
                page_chunks.append((chunk, page_num))
        else:
            logger.warning(f"PDF page {page_num} has no extractable text (scanned?)")

    # Build final chunks list with page prefix
    chunks = []
    for chunk_text, page_num in page_chunks:
        # Prefix each chunk with its page number so LLM and answers know the source
        tagged = f"[Page {page_num}] {chunk_text}"
        chunks.append(tagged)

    # Store page map in module-level cache for this parse session
    # Format: {chunk_index: page_number}
    _last_page_map.clear()
    for i, (_, page_num) in enumerate(page_chunks):
        _last_page_map[i] = page_num

    logger.debug(f"PDF parsed | pages={total_pages} | chunks={len(chunks)}")
    return chunks, None, "pdf"


# Module-level cache for page map (used by vector store metadata)
_last_page_map: dict = {}


def get_last_page_map() -> dict:
    """Returns page_index → page_number mapping from the last PDF parse."""
    return dict(_last_page_map)


def _parse_txt(content: bytes):
    text = content.decode("utf-8", errors="replace")
    chunks = split_text_smart(text)
    logger.debug(f"TXT parsed | chars={len(text)} | chunks={len(chunks)}")
    return chunks, None, "txt"


# ─────────────────────────────────────────────
# Smart sentence-aware chunking
# ─────────────────────────────────────────────

def split_text_smart(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> list[str]:
    """
    Sentence-aware chunking:
    1. Split text into sentences (never break mid-sentence)
    2. Group sentences into chunks of ~chunk_size words
    3. Overlap by repeating last N words of previous chunk

    This preserves context far better than word-splitting.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap    = overlap    or config.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    # ── Step 1: split into sentences ─────────
    sentences = _split_sentences(text)
    if not sentences:
        return []

    # ── Step 2: group sentences into chunks ──
    chunks = []
    current_words = []

    for sentence in sentences:
        sentence_words = sentence.split()
        if not sentence_words:
            continue

        # If adding this sentence would exceed chunk_size, flush first
        if current_words and len(current_words) + len(sentence_words) > chunk_size:
            chunk_text = " ".join(current_words).strip()
            if chunk_text:
                chunks.append(chunk_text)
            # Start new chunk with overlap from previous
            current_words = current_words[-overlap:] if overlap else []

        current_words.extend(sentence_words)

    # Flush the last chunk
    if current_words:
        chunk_text = " ".join(current_words).strip()
        if chunk_text:
            chunks.append(chunk_text)

    # Remove duplicate or near-empty chunks
    seen = set()
    unique = []
    for c in chunks:
        key = c[:80]
        if key not in seen and len(c.split()) >= 5:
            seen.add(key)
            unique.append(c)

    logger.debug(f"Smart chunking | sentences={len(sentences)} → chunks={len(unique)}")
    return unique


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences, handling common abbreviations."""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Split on sentence boundaries: . ! ? followed by space + capital letter
    # But NOT on abbreviations like Mr. Dr. e.g. etc.
    sentences = re.split(
        r'(?<=[.!?])\s+(?=[A-Z])',
        text
    )

    # Also split on double newlines (paragraph breaks)
    final = []
    for s in sentences:
        parts = re.split(r'\n\s*\n', s)
        final.extend(p.strip() for p in parts if p.strip())

    return final


def _clean_pdf_text(text: str) -> str:
    """Clean common PDF extraction artifacts."""
    # Remove excessive whitespace
    text = re.sub(r'[ \t]+', ' ', text)
    # Fix broken hyphenated words at line ends (e.g. "compu-\nter" → "computer")
    text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
    # Normalize line breaks
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Remove page numbers like "- 12 -" or "Page 12"
    text = re.sub(r'[-–]\s*\d+\s*[-–]', '', text)
    text = re.sub(r'\bPage\s+\d+\b', '', text, flags=re.IGNORECASE)
    return text.strip()


def _dataframe_to_chunks(df: pd.DataFrame) -> list[str]:
    return [
        " | ".join([f"{k}: {v}" for k, v in row.items() if pd.notna(v)])
        for row in df.to_dict(orient="records")
    ]


# Keep old split_text for backward compat
def split_text(text, chunk_size=None, overlap=None):
    return split_text_smart(text, chunk_size, overlap)