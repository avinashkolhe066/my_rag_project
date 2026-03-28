"""
Data Visualization Engine
─────────────────────────
Analyzes any tabular dataset (CSV/JSON) and returns:
- chart_data: structured JSON ready for Recharts
- kpis: key performance indicators
- insights: AI-written summary paragraph
- chart_types: which charts to render

Works for ANY dataset — employees, students, sales, inventory, etc.
Auto-detects column types and decides which charts make sense.
"""

import json
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)


def _detect_columns(df: pd.DataFrame) -> dict:
    """
    Auto-detect column roles:
    - name_col: the identifier column (name, employee, student, product etc.)
    - numeric_cols: all numeric columns
    - category_cols: low-cardinality string columns (department, grade, status etc.)
    - date_cols: date/time columns
    """
    name_keywords   = ["name", "employee", "student", "person", "product", "item", "title", "id"]
    cat_keywords    = ["department", "dept", "grade", "status", "category", "type", "group",
                       "division", "team", "class", "section", "gender", "role", "position"]

    name_col      = None
    numeric_cols  = []
    category_cols = []
    date_cols     = []

    for col in df.columns:
        col_lower = col.lower().replace(" ", "_").replace("-", "_")

        # Detect date columns
        if df[col].dtype in ["datetime64[ns]"] or any(k in col_lower for k in ["date", "time", "month", "year", "day"]):
            date_cols.append(col)
            continue

        # Detect numeric
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
            continue

        # Detect name/identifier
        if name_col is None and any(k in col_lower for k in name_keywords):
            name_col = col
            continue

        # Detect category (string with low cardinality)
        if df[col].dtype == object:
            unique_ratio = df[col].nunique() / max(len(df), 1)
            if unique_ratio < 0.3 or any(k in col_lower for k in cat_keywords):
                category_cols.append(col)
            elif name_col is None:
                name_col = col  # fallback: first string col is the identifier

    # Fallback: use first column as name
    if name_col is None and len(df.columns) > 0:
        name_col = df.columns[0]

    return {
        "name_col":      name_col,
        "numeric_cols":  numeric_cols,
        "category_cols": category_cols,
        "date_cols":     date_cols,
    }


def _safe_val(v):
    """Convert numpy types to Python native for JSON serialization."""
    if hasattr(v, "item"):
        return v.item()
    if pd.isna(v):
        return None
    return v


def build_visualization(df: pd.DataFrame, question: str, llm=None) -> dict:
    """
    Main function — takes a DataFrame and returns complete visualization data.

    Returns:
    {
      "charts": [ { "type": "bar", "title": "...", "data": [...], "keys": [...] }, ... ],
      "kpis":   [ { "label": "...", "value": "...", "color": "..." }, ... ],
      "insights": "AI written paragraph about the data",
      "total_records": 50,
      "dataset_label": "Employee Performance"
    }
    """
    if df.empty:
        return {"error": "No data found in the file."}

    cols   = _detect_columns(df)
    name   = cols["name_col"]
    nums   = cols["numeric_cols"]
    cats   = cols["category_cols"]
    dates  = cols["date_cols"]

    charts  = []
    kpis    = []

    total   = len(df)

    logger.info(f"Visualizer | rows={total} | name={name} | nums={nums} | cats={cats}")

    # ── KPI Cards ────────────────────────────────────────────────────────────
    kpi_colors = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]
    kpis.append({"label": "Total Records", "value": str(total), "color": "#6366f1"})

    for i, num_col in enumerate(nums[:5]):
        col_data = df[num_col].dropna()
        if col_data.empty:
            continue
        avg_val  = round(col_data.mean(), 2)
        max_val  = _safe_val(col_data.max())
        min_val  = _safe_val(col_data.min())
        color    = kpi_colors[(i + 1) % len(kpi_colors)]

        kpis.append({"label": f"Avg {num_col}",     "value": str(avg_val),  "color": color})
        kpis.append({"label": f"Highest {num_col}", "value": str(max_val),  "color": "#10b981"})
        kpis.append({"label": f"Lowest {num_col}",  "value": str(min_val),  "color": "#ef4444"})

    # ── Chart 1: Bar chart — all records by primary numeric column ────────────
    if name and nums:
        primary_num = nums[0]
        sorted_df   = df[[name, primary_num]].dropna().sort_values(primary_num, ascending=False)

        # Cap at 30 for readability — show top 30
        top_n    = sorted_df.head(30)
        bar_data = [
            {
                "name":  str(row[name])[:20],
                "value": round(_safe_val(row[primary_num]), 2)
            }
            for _, row in top_n.iterrows()
        ]

        charts.append({
            "type":     "bar",
            "title":    f"{primary_num} by {name}" + (" (Top 30)" if len(sorted_df) > 30 else ""),
            "data":     bar_data,
            "dataKey":  "value",
            "nameKey":  "name",
            "color":    "#6366f1",
            "total":    len(sorted_df),
        })

    # ── Chart 2: Multi-bar — all numeric columns for each record (top 15) ────
    if name and len(nums) >= 2:
        top15    = df.head(15)
        multi_data = []
        for _, row in top15.iterrows():
            entry = {"name": str(row[name])[:15]}
            for nc in nums[:4]:  # max 4 numeric cols
                entry[nc] = round(_safe_val(row[nc]), 2) if row[nc] is not None else 0
            multi_data.append(entry)

        charts.append({
            "type":    "multibar",
            "title":   f"Comparison across {', '.join(nums[:4])}",
            "data":    multi_data,
            "keys":    nums[:4],
            "colors":  ["#6366f1", "#06b6d4", "#10b981", "#f59e0b"],
        })

    # ── Chart 3: Pie chart — category distribution ───────────────────────────
    if cats:
        cat_col  = cats[0]
        cat_counts = df[cat_col].value_counts().head(10)
        pie_colors = ["#6366f1","#06b6d4","#10b981","#f59e0b","#ef4444","#8b5cf6","#ec4899","#14b8a6","#f97316","#84cc16"]
        pie_data = [
            {"name": str(k), "value": int(v), "color": pie_colors[i % len(pie_colors)]}
            for i, (k, v) in enumerate(cat_counts.items())
        ]
        charts.append({
            "type":  "pie",
            "title": f"Distribution by {cat_col}",
            "data":  pie_data,
        })

    # ── Chart 4: Category + Numeric — avg per category (grouped insight) ─────
    if cats and nums:
        cat_col = cats[0]
        num_col = nums[0]
        grp     = df.groupby(cat_col)[num_col].mean().round(2).reset_index()
        grp_data = [
            {"name": str(row[cat_col]), "value": _safe_val(row[num_col])}
            for _, row in grp.iterrows()
        ]
        charts.append({
            "type":    "bar",
            "title":   f"Average {num_col} by {cat_col}",
            "data":    grp_data,
            "dataKey": "value",
            "nameKey": "name",
            "color":   "#06b6d4",
        })

    # ── Chart 5: Line chart — trend over date or index ───────────────────────
    if dates and nums:
        date_col = dates[0]
        num_col  = nums[0]
        try:
            df[date_col] = pd.to_datetime(df[date_col])
            trend = df.groupby(date_col)[num_col].mean().round(2).reset_index()
            trend_data = [
                {"name": str(row[date_col])[:10], "value": _safe_val(row[num_col])}
                for _, row in trend.iterrows()
            ]
            charts.append({
                "type":    "line",
                "title":   f"{num_col} Trend over {date_col}",
                "data":    trend_data,
                "dataKey": "value",
                "nameKey": "name",
                "color":   "#10b981",
            })
        except Exception:
            pass
    elif nums and len(df) > 3:
        # No date col — show distribution as line (index-based trend)
        num_col    = nums[0]
        sorted_ser = df[num_col].dropna().sort_values().reset_index(drop=True)
        step       = max(1, len(sorted_ser) // 30)
        line_data  = [
            {"name": str(i + 1), "value": round(_safe_val(v), 2)}
            for i, v in enumerate(sorted_ser[::step])
        ]
        charts.append({
            "type":    "line",
            "title":   f"{num_col} Distribution (sorted)",
            "data":    line_data,
            "dataKey": "value",
            "nameKey": "name",
            "color":   "#10b981",
        })

    # ── AI Insights paragraph ─────────────────────────────────────────────────
    insights = _generate_insights(df, cols, kpis, question, llm)

    # ── Dataset label (guess from columns) ───────────────────────────────────
    dataset_label = _guess_dataset_label(df.columns.tolist())

    return {
        "charts":        charts,
        "kpis":          kpis[:9],   # max 9 KPI cards
        "insights":      insights,
        "total_records": total,
        "dataset_label": dataset_label,
        "columns":       df.columns.tolist(),
    }


def _generate_insights(df, cols, kpis, question, llm) -> str:
    """Use LLM to write a natural language insight paragraph about the data."""
    if llm is None:
        return _fallback_insights(df, cols, kpis)

    # Build a compact summary for the LLM
    name   = cols["name_col"]
    nums   = cols["numeric_cols"]
    cats   = cols["category_cols"]
    total  = len(df)

    summary_parts = [f"Dataset has {total} records."]

    if name and nums:
        primary = nums[0]
        top3    = df.nlargest(3, primary)[[name, primary]] if primary in df else None
        bot3    = df.nsmallest(3, primary)[[name, primary]] if primary in df else None
        if top3 is not None:
            summary_parts.append(f"Top 3 by {primary}: " +
                ", ".join(f"{row[name]} ({_safe_val(row[primary])})" for _, row in top3.iterrows()))
        if bot3 is not None:
            summary_parts.append(f"Bottom 3 by {primary}: " +
                ", ".join(f"{row[name]} ({_safe_val(row[primary])})" for _, row in bot3.iterrows()))

    for nc in nums[:3]:
        col_data = df[nc].dropna()
        if not col_data.empty:
            summary_parts.append(
                f"{nc}: avg={round(col_data.mean(),2)}, max={_safe_val(col_data.max())}, min={_safe_val(col_data.min())}"
            )

    if cats:
        cat_col = cats[0]
        dist    = df[cat_col].value_counts().head(5)
        summary_parts.append(f"{cat_col} distribution: " + ", ".join(f"{k}={v}" for k, v in dist.items()))

    data_summary = " | ".join(summary_parts)

    prompt = f"""You are a data analyst. Write a concise 3-4 sentence professional insight paragraph about this dataset.
Focus on: key findings, notable patterns, top/bottom performers, and one actionable recommendation.
Do NOT use bullet points. Write in flowing prose. Be specific with numbers.

Data summary: {data_summary}
User asked: {question}

Write the insights paragraph:"""

    try:
        return llm.generate(prompt).strip()
    except Exception:
        return _fallback_insights(df, cols, kpis)


def _fallback_insights(df, cols, kpis) -> str:
    """Generate basic insights without LLM."""
    name  = cols["name_col"]
    nums  = cols["numeric_cols"]
    total = len(df)

    parts = [f"The dataset contains {total} records."]

    if name and nums:
        primary = nums[0]
        if primary in df:
            top = df.loc[df[primary].idxmax(), name] if name in df else "N/A"
            bot = df.loc[df[primary].idxmin(), name] if name in df else "N/A"
            avg = round(df[primary].mean(), 2)
            parts.append(f"For {primary}: average is {avg}, highest is {_safe_val(df[primary].max())} ({top}), lowest is {_safe_val(df[primary].min())} ({bot}).")

    return " ".join(parts)


def _guess_dataset_label(columns: list) -> str:
    """Guess a human-friendly dataset name from column names."""
    cols_lower = " ".join(columns).lower()
    if any(k in cols_lower for k in ["employee", "salary", "department", "hire"]):
        return "Employee Data"
    if any(k in cols_lower for k in ["student", "grade", "marks", "score", "subject"]):
        return "Student Performance"
    if any(k in cols_lower for k in ["sales", "revenue", "product", "quantity", "order"]):
        return "Sales Data"
    if any(k in cols_lower for k in ["patient", "diagnosis", "treatment", "hospital"]):
        return "Medical Data"
    if any(k in cols_lower for k in ["inventory", "stock", "warehouse", "sku"]):
        return "Inventory Data"
    return "Dataset Analysis"