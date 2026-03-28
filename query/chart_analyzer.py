"""
Chart Analyzer Module
─────────────────────
Analyzes tabular data from SQL tables and generates chart data
for visualization. Uses the visualizer engine to create charts,
KPIs, and data previews.
"""

from query.visualizer import build_visualization
from utils.logger import get_logger

logger = get_logger(__name__)


class ChartAnalyzer:
    """
    Analyzes a SQL table and generates visualization data.
    """

    def __init__(self, db):
        self.db = db

    def analyze(self, sql_table: str, question: str) -> dict:
        """
        Analyze the table and return chart data dict.
        Returns dict with keys: charts, kpis, total_records, dataset_label, columns, data_preview
        Or {"error": "message"} on failure.
        """
        try:
            # Query the entire table
            df = self.db.run_query(f"SELECT * FROM {sql_table}")
            logger.info(f"ChartAnalyzer | table={sql_table} | rows={len(df)}")

            # Generate visualization data (without LLM insights)
            result = build_visualization(df, question, llm=None)

            # Add data preview for insights generation
            result["data_preview"] = df.head(10).to_dict("records")

            return result

        except Exception as e:
            logger.error(f"ChartAnalyzer error for table '{sql_table}': {e}")
            return {"error": str(e)}