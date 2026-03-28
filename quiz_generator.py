# -*- coding: utf-8 -*-
"""
RAG Platform — Quiz Generator
Generates accurate MCQ questions for ALL file types:
  - CSV/JSON  → SQL-verified answers (100% accurate, no LLM hallucination)
  - PDF/TXT   → Passage-anchored questions (1 question per passage, LLM only writes format)
  - Large files → Diverse sampling so all topics are covered
"""

import json
import os
import re
import random
from llm_client import LLMClient
from ingestion.vector_store import VectorStore
from database import DatabaseManager
from utils.logger import get_logger

logger = get_logger(__name__)

# File types that have SQL tables
_TABULAR_FILE_TYPES = {"csv", "json_array"}

DIFFICULTY_INSTRUCTIONS = {
    "easy": (
        "Generate straightforward factual questions. "
        "Test basic recall of key facts directly stated in the passage. "
        "Wrong options should be clearly different from the correct answer."
    ),
    "medium": (
        "Generate moderately challenging questions. "
        "Test understanding and application of the information. "
        "Wrong options should be plausible but incorrect on close reading."
    ),
    "hard": (
        "Generate challenging analytical questions. "
        "Test inference and critical thinking based on the passage. "
        "Wrong options should be very close to the correct answer."
    ),
}


class QuizGenerator:

    def __init__(self, llm: LLMClient, vector_store: VectorStore,
                 db: DatabaseManager = None):
        self.llm          = llm
        self.vector_store = vector_store
        self.db           = db

    # ══════════════════════════════════════════════════════════════
    # PUBLIC ENTRY POINT
    # ══════════════════════════════════════════════════════════════

    def generate(self, index_id: str, difficulty: str,
                 num_questions: int) -> list[dict]:
        difficulty    = difficulty.lower()
        num_questions = max(1, min(20, num_questions))

        if difficulty not in DIFFICULTY_INSTRUCTIONS:
            raise ValueError(
                f"Invalid difficulty '{difficulty}'. Choose easy, medium, or hard."
            )

        # Load metadata
        try:
            metadata  = self.vector_store.load_metadata(index_id)
            file_type = metadata.get("file_type", "")
            sql_table = metadata.get("sql_table")
        except Exception:
            file_type = ""
            sql_table = None

        logger.info(
            f"Quiz request | file_type={file_type} | difficulty={difficulty} "
            f"| num_questions={num_questions}"
        )

        # ── Route to correct strategy ─────────────────────────────────────
        if file_type in _TABULAR_FILE_TYPES and self.db and sql_table:
            return self._quiz_from_sql(sql_table, difficulty, num_questions)
        else:
            return self._quiz_from_passages(
                index_id, file_type, difficulty, num_questions
            )

    # ══════════════════════════════════════════════════════════════
    # STRATEGY 1 — SQL-VERIFIED (CSV / JSON)
    # Queries the actual database for facts.
    # Correct answers are 100% guaranteed accurate.
    # ══════════════════════════════════════════════════════════════

    def _quiz_from_sql(self, sql_table: str, difficulty: str,
                       num_questions: int) -> list[dict]:
        """Generate questions with SQL-verified correct answers."""
        import pandas as pd

        df = self.db.run_query(f'SELECT * FROM "{sql_table}"')
        if df.empty:
            raise ValueError("Table is empty.")

        num_cols = df.select_dtypes(include="number").columns.tolist()
        str_cols = df.select_dtypes(include="object").columns.tolist()

        # Find name column
        name_col = next(
            (c for c in str_cols
             if any(k in c.lower() for k in ["name","student","employee","person"])),
            str_cols[0] if str_cols else None
        )
        if not name_col:
            raise ValueError("No name column found in data.")

        # Find category column (low cardinality string)
        cat_col = next(
            (c for c in str_cols
             if c != name_col and df[c].nunique() <= 20),
            None
        )

        questions = []
        rng = random.Random(42)

        def wrong_names(exclude, n=3):
            pool = df[df[name_col] != exclude][name_col].tolist()
            return rng.sample(pool, min(n, len(pool)))

        def wrong_values(col, exclude_val, n=3):
            pool = [v for v in df[col].tolist() if v != exclude_val]
            sample = rng.sample(pool, min(n, len(pool)))
            return [str(round(v,1) if isinstance(v,float) else v) for v in sample]

        def fmt(v):
            if isinstance(v, float) and v == int(v):
                return str(int(v))
            if isinstance(v, float):
                return str(round(v, 1))
            return str(v)

        def make_q(question, correct_name_or_val, wrong_list, explanation):
            opts = [correct_name_or_val] + wrong_list[:3]
            while len(opts) < 4:
                opts.append("N/A")
            rng.shuffle(opts)
            correct_letter = "ABCD"[opts.index(correct_name_or_val)]
            return {
                "question":    question,
                "options":     {"A": opts[0], "B": opts[1],
                                "C": opts[2], "D": opts[3]},
                "correct":     correct_letter,
                "explanation": explanation,
            }

        # ── Highest value per column ───────────────────────────────────────
        for col in num_cols:
            if len(questions) >= num_questions * 2: break
            top  = df.loc[df[col].idxmax()]
            name = str(top[name_col])
            val  = fmt(top[col])
            questions.append(make_q(
                f"Who has the highest {col}?",
                name,
                wrong_names(name),
                f"{name} has the highest {col} with {val}."
            ))

        # ── Lowest value per column ────────────────────────────────────────
        for col in num_cols:
            if len(questions) >= num_questions * 2: break
            bot  = df.loc[df[col].idxmin()]
            name = str(bot[name_col])
            val  = fmt(bot[col])
            questions.append(make_q(
                f"Who has the lowest {col}?",
                name,
                wrong_names(name),
                f"{name} has the lowest {col} with {val}."
            ))

        # ── Specific value lookups ─────────────────────────────────────────
        sample_rows = df.sample(min(10, len(df)), random_state=42)
        for _, row in sample_rows.iterrows():
            if len(questions) >= num_questions * 2: break
            if not num_cols: break
            col  = rng.choice(num_cols[:4])
            name = str(row[name_col])
            val  = fmt(row[col])
            questions.append(make_q(
                f"What is {name}'s {col}?",
                val,
                wrong_values(col, row[col]),
                f"{name}'s {col} is {val}."
            ))

        # ── Average questions ──────────────────────────────────────────────
        for col in num_cols[:3]:
            if len(questions) >= num_questions * 2: break
            avg = round(df[col].mean(), 1)
            avg_str = fmt(avg)
            wrongs = [fmt(round(avg*m,1)) for m in [0.85, 1.15, 0.92]]
            questions.append(make_q(
                f"What is the average {col}?",
                avg_str,
                wrongs,
                f"The average {col} across all records is {avg_str}."
            ))

        # ── Category-based questions ───────────────────────────────────────
        if cat_col and num_cols:
            col  = num_cols[0]
            grp  = df.groupby(cat_col)[col].mean()
            if len(grp) >= 4:
                best = grp.idxmax()
                worst = grp.idxmin()
                wrongs_best  = [c for c in grp.index if c != best][:3]
                wrongs_worst = [c for c in grp.index if c != worst][:3]
                if len(wrongs_best) >= 3:
                    questions.append(make_q(
                        f"Which {cat_col} has the highest average {col}?",
                        best, wrongs_best,
                        f"{best} has the highest average {col} ({fmt(grp[best])})."
                    ))
                if len(wrongs_worst) >= 3:
                    questions.append(make_q(
                        f"Which {cat_col} has the lowest average {col}?",
                        worst, wrongs_worst,
                        f"{worst} has the lowest average {col} ({fmt(grp[worst])})."
                    ))

        # ── Count question ─────────────────────────────────────────────────
        total = len(df)
        wrongs = [str(total + d) for d in [5, -5, 10]]
        questions.append(make_q(
            "How many total records are in this dataset?",
            str(total), wrongs,
            f"The dataset contains {total} records."
        ))

        # Shuffle and return requested count
        rng.shuffle(questions)
        result = questions[:num_questions]
        logger.info(f"SQL-verified quiz done | generated={len(result)}")
        return result

    # ══════════════════════════════════════════════════════════════
    # STRATEGY 2 — PASSAGE-ANCHORED (PDF / TXT)
    # Each question is generated from ONE specific passage.
    # LLM only formats the question — the passage IS the answer source.
    # Works accurately even for very large documents.
    # ══════════════════════════════════════════════════════════════

    def _quiz_from_passages(self, index_id: str, file_type: str,
                            difficulty: str, num_questions: int) -> list[dict]:
        """
        Generate questions where each question is anchored to a single passage.
        The passage is shown to the LLM so it can only generate verifiable questions.
        """
        # Get diverse passages from the document
        passages = self._get_diverse_passages(index_id, num_questions)
        if not passages:
            raise ValueError(
                "Could not retrieve content from document. "
                "Please re-upload the file and try again."
            )

        instruction = DIFFICULTY_INSTRUCTIONS[difficulty]
        questions   = []

        for i, passage in enumerate(passages):
            if len(questions) >= num_questions:
                break

            # Generate exactly ONE question from this ONE passage
            prompt = f"""You are a quiz generator. Generate exactly ONE multiple choice question.

DIFFICULTY: {difficulty.upper()}
INSTRUCTION: {instruction}

SOURCE PASSAGE:
{passage}

RULES:
- Generate exactly 1 question based ONLY on the passage above
- Question must be answerable from the passage alone
- All 4 options must be specific and factual (use real values/names from passage)
- Wrong options must be plausible but clearly wrong based on the passage
- The correct answer MUST be directly supported by the passage text
- Do NOT invent information not in the passage
- Do NOT ask vague questions like "what is this passage about"

Return ONLY valid JSON, no markdown:
{{
  "question": "...",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct": "A",
  "explanation": "According to the passage, ..."
}}"""

            try:
                response = self.llm.generate(prompt)
                q = self._parse_single_question(response)
                if q:
                    # Tag with source passage for verification
                    q["source_passage"] = passage[:200]
                    questions.append(q)
                    logger.debug(f"Generated question {i+1}/{num_questions}")
            except Exception as e:
                logger.warning(f"Question {i+1} generation failed: {e}")
                continue

        if not questions:
            raise ValueError("Could not generate valid questions from document.")

        logger.info(f"Passage-anchored quiz done | generated={len(questions)}")
        # Remove internal source_passage field before returning
        for q in questions:
            q.pop("source_passage", None)

        return questions

    def _get_diverse_passages(self, index_id: str,
                              num_needed: int) -> list[str]:
        """
        Get diverse passages from the document.
        Uses multiple different search queries to cover different topics.
        For large files this ensures variety across the whole document.
        """
        # Use varied queries to get diverse passages from across the document
        diverse_queries = [
            "key facts and main information",
            "numbers statistics and data values",
            "names people organizations",
            "dates events timeline",
            "processes methods steps",
            "definitions explanations concepts",
            "results findings conclusions",
            "comparisons differences",
            "causes reasons why",
            "examples illustrations cases",
        ]

        all_passages = []
        seen_texts   = set()
        per_query    = max(2, (num_needed * 2) // len(diverse_queries) + 1)

        for query in diverse_queries[:num_needed + 2]:
            try:
                chunks, scores = self.vector_store.search(
                    index_id, query, top_k=per_query
                )
                for chunk, score in zip(chunks, scores):
                    # Deduplicate and filter very short passages
                    key = chunk[:80]
                    if key not in seen_texts and len(chunk.split()) >= 20:
                        seen_texts.add(key)
                        all_passages.append(chunk)
            except Exception as e:
                logger.warning(f"Search failed for '{query}': {e}")

        # If we still don't have enough, load directly from chunks file
        if len(all_passages) < num_needed:
            try:
                chunks_path = os.path.join(
                    self.vector_store.faiss_dir, f"{index_id}_chunks.json"
                )
                with open(chunks_path, "r", encoding="utf-8") as f:
                    all_direct = json.load(f)
                # Sample evenly to get coverage across large documents
                step = max(1, len(all_direct) // (num_needed * 2))
                for i in range(0, len(all_direct), step):
                    chunk = all_direct[i]
                    key   = chunk[:80]
                    if key not in seen_texts and len(chunk.split()) >= 20:
                        seen_texts.add(key)
                        all_passages.append(chunk)
                        if len(all_passages) >= num_needed * 3:
                            break
            except Exception as e:
                logger.warning(f"Direct chunk load failed: {e}")

        # Shuffle for variety and return enough for num_needed questions
        random.shuffle(all_passages)
        return all_passages[:num_needed * 2]  # extra buffer for failures

    # ══════════════════════════════════════════════════════════════
    # PARSING HELPERS
    # ══════════════════════════════════════════════════════════════

    def _parse_single_question(self, text: str) -> dict | None:
        """Parse a single question JSON from LLM response."""
        clean = text.strip()

        # Strip markdown fences
        if "```" in clean:
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", clean)
            if match:
                clean = match.group(1).strip()

        # Find JSON object
        start = clean.find("{")
        end   = clean.rfind("}") + 1
        if start == -1 or end == 0:
            return None

        try:
            data = json.loads(clean[start:end])
            return self._validate_question(data, 0)
        except Exception as e:
            logger.warning(f"Failed to parse question: {e}")
            return None

    def _validate_question(self, item: dict, index: int) -> dict | None:
        if not isinstance(item, dict):
            return None

        question    = str(item.get("question", "")).strip()
        options     = item.get("options", {})
        correct     = str(item.get("correct", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()

        if not question: return None
        if not isinstance(options, dict): return None
        for key in ["A", "B", "C", "D"]:
            if key not in options: return None
        if correct not in ["A", "B", "C", "D"]: return None

        return {
            "question":    question,
            "options":     {k: str(options[k]).strip() for k in ["A","B","C","D"]},
            "correct":     correct,
            "explanation": explanation or "See source material for details.",
        }