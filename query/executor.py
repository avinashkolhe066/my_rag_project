import json
from database import DatabaseManager
from ingestion.vector_store import VectorStore
from llm_client import LLMClient
from query.planner import QueryPlanner, QueryPlan
from utils.logger import get_logger

logger = get_logger(__name__)


class QueryExecutor:
    """
    Orchestrates the full query pipeline:
      1. Load metadata for the given index_id
      2. Decide query strategy (direct SQL / LLM-planned SQL / semantic search)
      3. Execute the chosen strategy
      4. Generate a final natural language answer via LLM
    """

    def __init__(self, llm: LLMClient, db: DatabaseManager, vector_store: VectorStore):
        self.llm = llm
        self.db = db
        self.vector_store = vector_store
        self.planner = QueryPlanner(llm)

    def execute(self, question: str, index_id: str, force_sql: bool = False) -> dict:
        """
        Main entry point. Returns a dict with at minimum an 'answer' key.
        Additional keys may include 'results', 'row_count', 'confidence'.
        """
        # ── Load index metadata ──────────────────────────────────────────
        try:
            metadata = self.vector_store.load_metadata(index_id)
        except FileNotFoundError:
            return {"answer": f"Index '{index_id}' not found. Please ingest a file first."}

        sql_table = metadata.get("sql_table")

        # ── Direct SQL path (user passed raw SELECT or forced SQL flag) ──
        if force_sql or question.strip().lower().startswith("select"):
            return self._run_direct_sql(question, sql_table)

        # ── LLM-planned path ─────────────────────────────────────────────
        plan: QueryPlan = self.planner.plan(question, sql_table)

        if plan.requires_sql and plan.sql_query:
            return self._run_planned_sql(question, plan)

        # ── Semantic search path ─────────────────────────────────────────
        return self._run_semantic_search(question, index_id)

    # ─────────────────────────────────────────
    # Strategy: Direct SQL
    # ─────────────────────────────────────────

    def _run_direct_sql(self, sql: str, sql_table: str | None) -> dict:
        if not sql_table:
            return {
                "answer": "This index does not contain tabular data. SQL queries are not supported."
            }
        try:
            df = self.db.run_query(sql)
            results = df.to_dict(orient="records")
            logger.info(f"Direct SQL returned {len(results)} rows")
            return {
                "answer": "Query executed successfully.",
                "results": results,
                "row_count": len(results),
            }
        except Exception as e:
            logger.error(f"Direct SQL failed: {e}")
            return {"answer": f"SQL execution failed: {str(e)}"}

    # ─────────────────────────────────────────
    # Strategy: LLM-Planned SQL
    # ─────────────────────────────────────────

    def _run_planned_sql(self, question: str, plan: QueryPlan) -> dict:
        try:
            df = self.db.run_query(plan.sql_query)
        except Exception as e:
            logger.error(f"Planned SQL failed: {e}")
            return {"answer": f"SQL execution failed: {str(e)}"}

        # Aggregation → single value answer
        if plan.is_aggregate:
            value = df.iloc[0, 0] if not df.empty else "No result"
            return {"answer": f"The result is: {value}"}

        results = df.to_dict(orient="records")
        top_results = results[:10]
        total = len(results)

        prompt = f"""User question: {question}

Total matching records: {total}
Top results (up to 10):
{json.dumps(top_results, indent=2)}

Instructions:
- Clearly state the total number of matching records.
- Summarize or list the top results.
- If a recommendation was requested, suggest the best option with a reason.
- Do not invent or assume any data not shown above.
"""
        try:
            answer = self.llm.generate(prompt)
            logger.info("Planned SQL answer generated successfully")
            return {"answer": answer, "row_count": total}
        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")
            return {"answer": f"LLM error while generating answer: {str(e)}"}

    # ─────────────────────────────────────────
    # Strategy: Semantic Search
    # ─────────────────────────────────────────

    def _run_semantic_search(self, question: str, index_id: str) -> dict:
        try:
            chunks, distances = self.vector_store.search(index_id, question)
        except FileNotFoundError as e:
            return {"answer": str(e)}
        except Exception as e:
            logger.error(f"FAISS search failed: {e}")
            return {"answer": f"Search failed: {str(e)}"}

        if not chunks:
            return {"answer": "No relevant content found for your question."}

        prompt = f"""User question: {question}

Relevant content retrieved from the document:
{json.dumps(chunks, indent=2)}

Using only the above content, provide a clear and helpful answer.
Do not invent information that is not present in the content above.
"""
        try:
            answer = self.llm.generate(prompt)
            confidence = round(1 / (1 + distances[0]), 4) if distances else 0.0
            logger.info(f"Semantic search answer generated | confidence={confidence}")
            return {"answer": answer, "confidence": confidence}
        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")
            return {"answer": f"LLM error while generating answer: {str(e)}"}
