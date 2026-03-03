import json
from llm_client import LLMClient
from utils.logger import get_logger

logger = get_logger(__name__)


class QueryPlan:
    """Holds the result of LLM query planning."""

    def __init__(self, requires_sql: bool, is_aggregate: bool, sql_query: str | None):
        self.requires_sql = requires_sql
        self.is_aggregate = is_aggregate
        self.sql_query = sql_query

    def __repr__(self):
        return (
            f"QueryPlan(requires_sql={self.requires_sql}, "
            f"is_aggregate={self.is_aggregate}, "
            f"sql_query={self.sql_query!r})"
        )


class QueryPlanner:
    """
    Uses the LLM to analyze a natural language question and decide:
      - Should we run a SQL query or use semantic search?
      - Is it an aggregation query (COUNT, SUM, AVG, etc.)?
      - What SQL should we run (if applicable)?
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(self, question: str, sql_table: str | None) -> QueryPlan:
        """
        Analyze the question and return a QueryPlan.
        Falls back to semantic search if planning fails.
        """
        if not sql_table:
            # No tabular data available — always use semantic search
            logger.debug("No sql_table available, defaulting to semantic search")
            return QueryPlan(requires_sql=False, is_aggregate=False, sql_query=None)

        prompt = self._build_prompt(question, sql_table)

        try:
            response_text = self.llm.generate(prompt)
            plan = self._parse_response(response_text)
            logger.info(f"Query plan resolved: {plan}")
            return plan
        except Exception as e:
            logger.warning(f"Query planning failed, falling back to semantic search: {e}")
            return QueryPlan(requires_sql=False, is_aggregate=False, sql_query=None)

    # ─────────────────────────────────────────
    # Private
    # ─────────────────────────────────────────

    def _build_prompt(self, question: str, sql_table: str) -> str:
        return f"""You are a query planner for a hybrid search system.
The data is stored in a SQLite table named "{sql_table}".

Decide whether the following question requires SQL or plain text search.

Use SQL when the question involves:
- Counting records
- Aggregations (COUNT, AVG, SUM, MIN, MAX)
- Filtering by specific values (price < 500, category = 'electronics')
- Sorting or ranking
- Grouping

Return ONLY valid JSON with no extra text, no markdown, no explanation:

{{
  "requires_sql": true or false,
  "is_aggregate": true or false,
  "sql_query": "SELECT ... FROM {sql_table} WHERE ..." or null
}}

Question: {question}
"""

    def _parse_response(self, text: str) -> QueryPlan:
        """Parse the LLM JSON response into a QueryPlan object."""
        # Strip markdown code fences if present
        clean = text.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        data = json.loads(clean)

        return QueryPlan(
            requires_sql=bool(data.get("requires_sql", False)),
            is_aggregate=bool(data.get("is_aggregate", False)),
            sql_query=data.get("sql_query") or None,
        )
