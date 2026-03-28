import json
from llm_client import LLMClient
from utils.logger import get_logger

logger = get_logger(__name__)

# SQL keywords that clearly indicate a raw SQL query from the user
_SQL_START = ("select ", "select\n", "select\t")


def is_raw_sql(text: str) -> bool:
    """Return True if the user's input looks like a raw SQL SELECT statement."""
    return text.strip().lower().startswith(_SQL_START)


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
    Decides whether a natural language question should be answered via SQL or RAG.

    Key improvement: the real table schema (column names + types) is passed to
    the LLM so it generates accurate SQL instead of guessing column names.
    """

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def plan(
        self,
        question: str,
        sql_table: str | None,
        schema: list[dict] | None = None,
    ) -> QueryPlan:
        """
        Analyze the question and return a QueryPlan.

        Args:
            question:  the user's natural language question
            sql_table: SQLite table name (None for PDF/TXT files)
            schema:    list of {"name": col, "type": type} dicts from PRAGMA table_info

        Returns QueryPlan. Falls back to RAG if planning fails.
        """
        # PDF / TXT — no SQL table, always use RAG
        if not sql_table:
            logger.debug("No sql_table -> using RAG")
            return QueryPlan(requires_sql=False, is_aggregate=False, sql_query=None)

        # Build schema string for the prompt
        if schema:
            schema_str = ", ".join([f"{col['name']} ({col['type']})" for col in schema])
        else:
            schema_str = "unknown (schema not available)"

        prompt = self._build_prompt(question, sql_table, schema_str)

        try:
            response_text = self.llm.generate(prompt)
            plan = self._parse_response(response_text)
            logger.info(f"Query plan: {plan}")
            return plan
        except Exception as e:
            logger.warning(f"Query planning failed, falling back to RAG: {e}")
            return QueryPlan(requires_sql=False, is_aggregate=False, sql_query=None)

    # ─────────────────────────────────────────
    # Private
    # ─────────────────────────────────────────

    def _build_prompt(self, question: str, sql_table: str, schema_str: str) -> str:
        # Build quoted column list — critical for columns with spaces/special chars
        quoted_cols = self._quoted_columns_hint(schema_str)

        return f"""You are an expert SQL query planner for SQLite.

Table name : "{sql_table}"
Columns    : {schema_str}

CRITICAL QUOTING RULES — you MUST follow these exactly:
1. ALWAYS wrap column names in double quotes: "Column Name"
2. This is mandatory for ALL columns, especially ones with spaces or special characters
3. Use the EXACT column names from the list above — do NOT rename or guess
4. Use the EXACT table name: {sql_table}
5. Do NOT use underscores for spaces — "Project Name" not Project_Name
6. Do NOT use any other table name like 'transactions' or 'your_table'

Column reference guide (copy these EXACTLY into your SQL):
{quoted_cols}

For name/text searches: use LIKE with wildcards
  Example: WHERE "Party 1" LIKE '%vikash kumar%'
  NOT: WHERE "Party 1" = 'vikash kumar'

Use SQL when the question involves:
- Counting, filtering, sorting, grouping, aggregation (COUNT, AVG, SUM, MIN, MAX)
- Specific value lookups, rankings, comparisons, top/bottom N

Use semantic search (requires_sql: false) when:
- The question asks for explanations or summaries that need document context
- The question cannot be answered by querying the data columns

Return ONLY valid JSON — no markdown fences, no explanation, no extra text:

{{
  "requires_sql": true or false,
  "is_aggregate": true or false,
  "sql_query": "SELECT \"col1\", \"col2\" FROM \"{sql_table}\" WHERE ..." or null
}}

Question: {question}
"""

    def _quoted_columns_hint(self, schema_str: str) -> str:
        """Build a quoted column reference list from schema string."""
        lines = []
        for part in schema_str.split(", "):
            col_name = part.split(" (")[0].strip()
            lines.append(f'  "{col_name}"')
        return "\n".join(lines)

    def _parse_response(self, text: str) -> QueryPlan:
        """Parse LLM JSON response into a QueryPlan. Strips markdown fences if present."""
        clean = text.strip()

        # Strip ```json ... ``` fences
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.lower().startswith("json"):
                clean = clean[4:]

        clean = clean.strip()
        data = json.loads(clean)

        return QueryPlan(
            requires_sql=bool(data.get("requires_sql", False)),
            is_aggregate=bool(data.get("is_aggregate", False)),
            sql_query=data.get("sql_query") or None,
        )