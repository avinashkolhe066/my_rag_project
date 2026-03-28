import sqlite3
import pandas as pd
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Handles all SQLite operations: saving DataFrames as tables
    and executing SELECT queries safely.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.DB_PATH
        logger.info(f"DatabaseManager initialized | db={self.db_path}")

    def save_dataframe(self, df: pd.DataFrame, table_name: str) -> None:
        """Save a pandas DataFrame as a SQLite table (replaces if exists)."""
        try:
            conn = sqlite3.connect(self.db_path)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            conn.close()
            logger.info(
                f"Saved DataFrame to table '{table_name}' "
                f"({len(df)} rows, {len(df.columns)} cols)"
            )
        except Exception as e:
            logger.error(f"Failed to save DataFrame to '{table_name}': {e}")
            raise

    def run_query(self, sql: str) -> pd.DataFrame:
        """
        Execute a SELECT query and return results as a DataFrame.
        Raises ValueError for non-SELECT queries (security guard).
        """
        clean_sql = sql.strip()

        if not clean_sql.lower().startswith("select"):
            logger.warning(f"Blocked non-SELECT query: {clean_sql[:80]}")
            raise ValueError("Only SELECT queries are permitted for security reasons.")

        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(clean_sql, conn)
            conn.close()
            logger.info(f"Query executed successfully | rows={len(df)}")
            return df
        except Exception as e:
            logger.error(f"SQL execution failed: {e} | query={clean_sql[:120]}")
            raise

    def get_table_schema(self, table_name: str) -> list[dict]:
        """
        Return column names and types for a given table.
        Used to pass schema info to the LLM so it generates accurate SQL.
        Example return: [{"name": "price", "type": "REAL"}, ...]
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            rows = cursor.fetchall()
            conn.close()
            schema = [{"name": row[1], "type": row[2]} for row in rows]
            logger.debug(f"Schema for '{table_name}': {schema}")
            return schema
        except Exception as e:
            logger.error(f"get_table_schema failed: {e}")
            return []

    def table_exists(self, table_name: str) -> bool:
        """Check whether a table exists in the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception as e:
            logger.error(f"table_exists check failed: {e}")
            return False