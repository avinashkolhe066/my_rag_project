import json
import pandas as pd
import PyPDF2
from io import BytesIO
from typing import Tuple, Optional
from utils.logger import get_logger
import config

logger = get_logger(__name__)

# Supported extensions
SUPPORTED_EXTENSIONS = {".csv", ".json", ".pdf", ".txt"}


def get_extension(filename: str) -> str:
    """Return the lowercased file extension e.g. '.csv'"""
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def parse_file(
    content: bytes, filename: str
) -> Tuple[list[str], Optional[pd.DataFrame], str]:
    """
    Parse an uploaded file and return:
        chunks    — list of text strings for embedding
        dataframe — pandas DataFrame if tabular, else None
        file_type — human-readable label e.g. 'csv', 'pdf'

    Raises ValueError for unsupported file types.
    """
    ext = get_extension(filename)

    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Allowed types: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    logger.info(f"Parsing file | name={filename} | ext={ext}")

    if ext == ".csv":
        return _parse_csv(content)

    elif ext == ".json":
        return _parse_json(content)

    elif ext == ".pdf":
        return _parse_pdf(content)

    elif ext == ".txt":
        return _parse_txt(content)


# ─────────────────────────────────────────────
# Private parsers
# ─────────────────────────────────────────────

def _parse_csv(content: bytes) -> Tuple[list[str], pd.DataFrame, str]:
    df = pd.read_csv(BytesIO(content))
    chunks = _dataframe_to_chunks(df)
    logger.debug(f"CSV parsed | rows={len(df)} | chunks={len(chunks)}")
    return chunks, df, "csv"


def _parse_json(content: bytes) -> Tuple[list[str], Optional[pd.DataFrame], str]:
    data = json.loads(content)

    # If it's a list of dicts → treat as tabular data
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        df = pd.DataFrame(data)
        chunks = _dataframe_to_chunks(df)
        logger.debug(f"JSON array parsed | rows={len(df)} | chunks={len(chunks)}")
        return chunks, df, "json_array"

    # Otherwise treat as plain text
    text = json.dumps(data, indent=2)
    chunks = split_text(text)
    logger.debug(f"JSON object parsed | chunks={len(chunks)}")
    return chunks, None, "json"


def _parse_pdf(content: bytes) -> Tuple[list[str], None, str]:
    pdf_reader = PyPDF2.PdfReader(BytesIO(content))
    text = ""
    for i, page in enumerate(pdf_reader.pages):
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
        else:
            logger.warning(f"PDF page {i+1} returned no text (possibly scanned image)")

    chunks = split_text(text)
    logger.debug(f"PDF parsed | pages={len(pdf_reader.pages)} | chunks={len(chunks)}")
    return chunks, None, "pdf"


def _parse_txt(content: bytes) -> Tuple[list[str], None, str]:
    text = content.decode("utf-8", errors="replace")
    chunks = split_text(text)
    logger.debug(f"TXT parsed | chars={len(text)} | chunks={len(chunks)}")
    return chunks, None, "txt"


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _dataframe_to_chunks(df: pd.DataFrame) -> list[str]:
    """Convert each row of a DataFrame into a single text chunk."""
    return [
        " ".join([f"{k} is {v}" for k, v in row.items()])
        for row in df.to_dict(orient="records")
    ]


def split_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
) -> list[str]:
    """
    Split a long text into overlapping word-based chunks.
    Uses config defaults if chunk_size / overlap are not provided.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    words = text.split()
    if not words:
        return []

    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)

    return chunks
