# -*- coding: utf-8 -*-
"""
RAG Platform — Dynamic PDF Report Generator
Analyzes actual columns in the dataframe and builds a fully custom report.
No fixed templates — every section and chart is decided from the data.
"""

import io
import os
import warnings
warnings.filterwarnings("ignore")


def generate_pdf(df, insights: str, dataset_label: str,
                 filename: str, filter_info: dict = None) -> str:

    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Image,
        Table, TableStyle, PageBreak, HRFlowable, Flowable
    )

    # ── Output path ────────────────────────────────────────────────
    out_dir = os.path.join(os.path.dirname(__file__), "generated_reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, filename)

    # ── Colors ─────────────────────────────────────────────────────
    C = {
        "navy":    "#0D1B2A",
        "indigo":  "#4361EE",
        "blue":    "#0096C7",
        "green":   "#2DC653",
        "amber":   "#F4A261",
        "red":     "#E63946",
        "violet":  "#7209B7",
        "teal":    "#0B7285",
        "bg":      "#F8FAFC",
        "border":  "#E2E8F0",
        "text":    "#1E293B",
        "muted":   "#64748B",
        "white":   "#FFFFFF",
    }
    PALETTE = ["#4361EE","#0096C7","#2DC653","#F4A261",
               "#E63946","#7209B7","#0B7285","#F97316",
               "#06B6D4","#84CC16","#F59E0B","#EF4444"]

    def hx(h):
        h = h.lstrip("#")
        return colors.Color(*[int(h[i:i+2],16)/255 for i in (0,2,4)])

    def mhx(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))

    def fig2buf(fig):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        buf.seek(0)
        return buf

    def polish(ax, xgrid=False, ygrid=True):
        ax.set_facecolor(C["bg"])
        if ygrid:
            ax.grid(axis="y", color="#CBD5E1", lw=0.5, ls="--", alpha=0.7, zorder=0)
        if xgrid:
            ax.grid(axis="x", color="#CBD5E1", lw=0.5, ls="--", alpha=0.7, zorder=0)
        for sp in ("top","right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left","bottom"):
            ax.spines[sp].set_color("#CBD5E1")
            ax.spines[sp].set_lw(0.6)
        ax.tick_params(colors=C["muted"], labelsize=8, length=3)

    # ── Styles ─────────────────────────────────────────────────────
    def PS(name, **kw):
        kw.setdefault("fontName","Helvetica")
        return ParagraphStyle(name, **kw)

    TITLE  = PS("t",  fontName="Helvetica-Bold", fontSize=22,
                textColor=hx(C["white"]), spaceAfter=4)
    SUB    = PS("s",  fontSize=10, textColor=hx(C["border"]), spaceAfter=2)
    H1     = PS("h1", fontName="Helvetica-Bold", fontSize=13,
                textColor=hx(C["white"]), spaceAfter=0)
    BODY   = PS("b",  fontSize=9, textColor=hx(C["text"]),
                leading=15, spaceAfter=6, alignment=TA_JUSTIFY)
    SMALL  = PS("sm", fontSize=8, textColor=hx(C["muted"]), spaceAfter=4)
    CAP    = PS("cp", fontSize=7.5, textColor=hx(C["muted"]),
                alignment=TA_CENTER, spaceAfter=8, spaceBefore=2)
    TH     = PS("th", fontName="Helvetica-Bold", fontSize=8,
                textColor=colors.white, alignment=TA_CENTER)
    TC     = PS("tc", fontSize=8, textColor=hx(C["text"]), alignment=TA_CENTER)

    def SP(n=6): return Spacer(1, n)
    def HR():    return HRFlowable(width="100%", thickness=0.5,
                                   color=hx(C["border"]), spaceAfter=8)

    # ── Section header ──────────────────────────────────────────────
    class SectionHeader(Flowable):
        def __init__(self, num, title, color=None):
            super().__init__()
            self.num   = num
            self.title = title
            self.color = color or C["indigo"]
            self.width = 170*mm
            self.height = 22

        def draw(self):
            c = self.canv
            c.setFillColor(hx(self.color))
            c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 9)
            c.drawString(10, 7, f"{self.num:02d}  {self.title.upper()}")

    # ── Insight card ────────────────────────────────────────────────
    class InsightCard(Flowable):
        def __init__(self, icon, title, value, sub="", color=None):
            super().__init__()
            self.icon  = icon
            self.title = title
            self.value = value
            self.sub   = sub
            self.color = color or C["indigo"]
            self.width = 38*mm
            self.height= 28

        def draw(self):
            c = self.canv
            c.setStrokeColor(hx(self.color))
            c.setFillColor(hx(C["bg"]))
            c.roundRect(0,0,self.width,self.height,4,fill=1,stroke=1)
            c.setFillColor(hx(self.color))
            c.setFont("Helvetica-Bold",7)
            c.drawString(6,19, self.title.upper())
            c.setFont("Helvetica-Bold",12)
            c.setFillColor(hx(C["text"]))
            c.drawString(6,9, str(self.value)[:14])
            if self.sub:
                c.setFont("Helvetica",6.5)
                c.setFillColor(hx(C["muted"]))
                c.drawString(6,2, str(self.sub)[:22])

    # ══════════════════════════════════════════════════════════════
    # COLUMN ANALYSIS — understand what every column actually is
    # ══════════════════════════════════════════════════════════════
    num_cols = df.select_dtypes(include="number").columns.tolist()
    str_cols = df.select_dtypes(include="object").columns.tolist()
    all_cols = df.columns.tolist()

    def col_matches(col, keywords):
        cl = col.lower()
        return any(k in cl for k in keywords)

    # Identify name column
    name_col = next((c for c in str_cols if col_matches(c,
        ["name","student","employee","person","emp","staff"])), None)
    if not name_col and str_cols:
        name_col = str_cols[0]

    def fname(v):
        return str(v).split()[0] if v and str(v).strip() else str(v)

    # Identify categorical grouping column
    cat_col = next((c for c in str_cols if c != name_col and col_matches(c,
        ["dept","department","team","city","location","class","grade",
         "group","category","division","section","branch","region"])), None)
    if not cat_col:
        # Pick any string col with low cardinality
        for c in str_cols:
            if c != name_col and df[c].nunique() <= 20:
                cat_col = c
                break

    # Identify primary ranking/score column
    rank_col = next((c for c in num_cols if col_matches(c,
        ["total","salary","sal","pay","wage","income","revenue",
         "score","marks","cgpa","gpa","amount","ctc"])), None)
    if not rank_col and num_cols:
        rank_col = max(num_cols, key=lambda c: df[c].max())

    # Identify percentage/rating column
    pct_col = next((c for c in num_cols if col_matches(c,
        ["percent","percentage","rate","ratio","rating","grade"])), None)
    if pct_col == rank_col:
        pct_col = None

    # Identify a secondary numeric (attendance, experience, age, etc.)
    sec_col = next((c for c in num_cols if col_matches(c,
        ["attendance","experience","exp","age","tenure","years","present"])), None)

    # Collect all subject-like columns (multiple numeric cols with similar ranges)
    subject_cols = []
    if num_cols:
        # Group numeric cols by value range — subjects usually share same max
        maxvals = {c: df[c].max() for c in num_cols}
        if len(num_cols) >= 3:
            # Find the modal max value
            from collections import Counter
            modal_max = Counter([round(v,-1) for v in maxvals.values()]).most_common(1)[0][0]
            subject_cols = [c for c in num_cols
                            if abs(maxvals[c] - modal_max) <= modal_max * 0.3
                            and c not in [rank_col, pct_col, sec_col]]

    # ══════════════════════════════════════════════════════════════
    # CHART BUILDERS — each returns an image buffer or None
    # ══════════════════════════════════════════════════════════════

    chart_num = [0]
    story_charts = []  # [(title, buf, caption)]

    def add_chart(title, buf, caption):
        if buf:
            story_charts.append((title, buf, caption))

    # Chart 1: Ranking bar — top N by rank_col
    def chart_ranking():
        if not rank_col or not name_col: return None
        n   = min(20, len(df))
        top = df.nlargest(n, rank_col)[[name_col, rank_col]].reset_index(drop=True)
        vals= top[rank_col].values
        lbls= [fname(v) for v in top[name_col].values]

        # Color by quartile
        q75 = np.percentile(df[rank_col].dropna(), 75)
        q25 = np.percentile(df[rank_col].dropna(), 25)
        bar_colors = [mhx(C["green"]) if v >= q75
                      else mhx(C["amber"]) if v >= q25
                      else mhx(C["red"]) for v in vals]

        fig, ax = plt.subplots(figsize=(7, max(3, n*0.32)))
        fig.patch.set_facecolor(C["bg"])
        bars = ax.barh(range(len(vals)), vals, color=bar_colors,
                       height=0.7, zorder=3)
        ax.set_yticks(range(len(lbls)))
        ax.set_yticklabels(lbls, fontsize=8)
        ax.invert_yaxis()
        for bar, val in zip(bars, vals):
            ax.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
                    f"{val:,.1f}" if isinstance(val,float) else f"{val:,}",
                    va="center", ha="left", fontsize=7, color=C["text"])
        ax.axvline(df[rank_col].mean(), color=C["indigo"], lw=1.2,
                   ls="--", label=f"Avg {df[rank_col].mean():,.1f}", zorder=4)
        ax.legend(fontsize=7, loc="lower right")
        ax.set_xlabel(rank_col, fontsize=8)
        ax.set_title(f"Top {n} by {rank_col}", fontsize=10,
                     fontweight="bold", color=C["text"], pad=8)
        polish(ax, xgrid=True, ygrid=False)
        plt.tight_layout()
        return fig2buf(fig)

    # Chart 2: Subject / multi-column radar or grouped bar
    def chart_subject_comparison():
        if len(subject_cols) < 2: return None
        cols_to_use = subject_cols[:8]
        avgs = [df[c].mean() for c in cols_to_use]

        fig, ax = plt.subplots(figsize=(7, 3.5))
        fig.patch.set_facecolor(C["bg"])
        x = range(len(cols_to_use))
        bar_colors = [PALETTE[i % len(PALETTE)] for i in x]
        bars = ax.bar(x, avgs, color=bar_colors, width=0.6, zorder=3, edgecolor="white", lw=0.5)
        ax.set_xticks(list(x))
        ax.set_xticklabels(cols_to_use, fontsize=9, rotation=15, ha="right")
        for bar, val in zip(bars, avgs):
            ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=8, fontweight="bold")
        ax.set_ylabel("Average Score", fontsize=8)
        ax.set_title(f"Average Score per Subject", fontsize=10,
                     fontweight="bold", color=C["text"], pad=8)
        polish(ax)
        plt.tight_layout()
        return fig2buf(fig)

    # Chart 3: Distribution histogram of rank_col
    def chart_distribution():
        if not rank_col: return None
        vals = df[rank_col].dropna()
        if len(vals) < 4: return None

        fig, ax = plt.subplots(figsize=(7, 3))
        fig.patch.set_facecolor(C["bg"])
        n_bins = min(15, max(5, len(vals)//4))
        n, bins, patches = ax.hist(vals, bins=n_bins, edgecolor="white",
                                   linewidth=0.5, zorder=3)
        # Color by value
        for patch, left in zip(patches, bins):
            if left >= np.percentile(vals, 75):
                patch.set_facecolor(mhx(C["green"]))
            elif left >= np.percentile(vals, 25):
                patch.set_facecolor(mhx(C["blue"]))
            else:
                patch.set_facecolor(mhx(C["amber"]))
        ax.axvline(vals.mean(), color=C["indigo"], lw=1.5, ls="--",
                   label=f"Mean: {vals.mean():.1f}", zorder=4)
        ax.axvline(vals.median(), color=C["red"], lw=1.2, ls=":",
                   label=f"Median: {vals.median():.1f}", zorder=4)
        ax.legend(fontsize=8)
        ax.set_xlabel(rank_col, fontsize=8)
        ax.set_ylabel("Count", fontsize=8)
        ax.set_title(f"{rank_col} Distribution", fontsize=10,
                     fontweight="bold", color=C["text"], pad=8)
        polish(ax)
        plt.tight_layout()
        return fig2buf(fig)

    # Chart 4: Category breakdown
    def chart_category():
        if not cat_col or not rank_col: return None
        grp = df.groupby(cat_col)[rank_col].mean().sort_values(ascending=False)
        if len(grp) < 2 or len(grp) > 25: return None

        fig, ax = plt.subplots(figsize=(7, max(3, len(grp)*0.35)))
        fig.patch.set_facecolor(C["bg"])
        bar_colors = [PALETTE[i % len(PALETTE)] for i in range(len(grp))]
        bars = ax.barh(range(len(grp)), grp.values, color=bar_colors,
                       height=0.6, zorder=3)
        ax.set_yticks(range(len(grp)))
        ax.set_yticklabels(grp.index, fontsize=8)
        ax.invert_yaxis()
        for bar, val in zip(bars, grp.values):
            ax.text(bar.get_width()+0.2, bar.get_y()+bar.get_height()/2,
                    f"{val:.1f}", va="center", ha="left", fontsize=7)
        ax.set_xlabel(f"Avg {rank_col}", fontsize=8)
        ax.set_title(f"Avg {rank_col} by {cat_col}", fontsize=10,
                     fontweight="bold", color=C["text"], pad=8)
        polish(ax, xgrid=True, ygrid=False)
        plt.tight_layout()
        return fig2buf(fig)

    # Chart 5: Scatter — secondary vs rank
    def chart_scatter():
        if not sec_col or not rank_col or not name_col: return None
        d = df[[name_col, rank_col, sec_col]].dropna()
        if len(d) < 4: return None

        fig, ax = plt.subplots(figsize=(7, 3.5))
        fig.patch.set_facecolor(C["bg"])
        q75 = np.percentile(d[rank_col], 75)
        dot_colors = [mhx(C["green"]) if v >= q75
                      else mhx(C["amber"]) if v >= np.percentile(d[rank_col],25)
                      else mhx(C["red"]) for v in d[rank_col]]
        ax.scatter(d[sec_col], d[rank_col], c=dot_colors, s=70, zorder=3,
                   edgecolors="white", linewidths=0.5, alpha=0.85)
        # Annotate top 5
        top5 = d.nlargest(5, rank_col)
        for _, row in top5.iterrows():
            ax.annotate(fname(row[name_col]),
                        (row[sec_col], row[rank_col]),
                        fontsize=6.5, color=C["text"],
                        xytext=(3,3), textcoords="offset points")
        # Trend line
        try:
            z  = np.polyfit(d[sec_col], d[rank_col], 1)
            px = np.linspace(d[sec_col].min(), d[sec_col].max(), 100)
            ax.plot(px, np.poly1d(z)(px), "--", color=C["indigo"],
                    lw=1.2, alpha=0.7, label="Trend")
            ax.legend(fontsize=8)
        except Exception:
            pass
        ax.set_xlabel(sec_col, fontsize=8)
        ax.set_ylabel(rank_col, fontsize=8)
        ax.set_title(f"{sec_col} vs {rank_col}", fontsize=10,
                     fontweight="bold", color=C["text"], pad=8)
        polish(ax)
        plt.tight_layout()
        return fig2buf(fig)

    # Chart 6: Pie/donut for categorical distribution
    def chart_category_pie():
        if not cat_col: return None
        counts = df[cat_col].value_counts()
        if len(counts) < 2 or len(counts) > 12: return None

        fig, ax = plt.subplots(figsize=(5.5, 3.5))
        fig.patch.set_facecolor(C["bg"])
        wedge_colors = [PALETTE[i % len(PALETTE)] for i in range(len(counts))]
        wedges, texts, autotexts = ax.pie(
            counts.values, labels=counts.index,
            colors=wedge_colors, autopct="%1.1f%%",
            startangle=90, pctdistance=0.8,
            wedgeprops={"edgecolor":"white","linewidth":1.2},
            textprops={"fontsize":8}
        )
        for at in autotexts:
            at.set_fontsize(7)
            at.set_color("white")
        # Draw donut hole
        hole = plt.Circle((0,0), 0.55, color=C["bg"])
        ax.add_patch(hole)
        ax.set_title(f"Distribution by {cat_col}", fontsize=10,
                     fontweight="bold", color=C["text"], pad=8)
        plt.tight_layout()
        return fig2buf(fig)

    # Chart 7: pct_col or sec_col distribution bar
    def chart_secondary_dist():
        if not sec_col and not pct_col: return None
        col = pct_col or sec_col
        vals = df[col].dropna()
        if len(vals) < 4: return None

        fig, ax = plt.subplots(figsize=(7, 3))
        fig.patch.set_facecolor(C["bg"])
        n_bins = min(12, max(4, len(vals)//4))
        n, bins, patches = ax.hist(vals, bins=n_bins, color=mhx(C["blue"]),
                                   edgecolor="white", lw=0.5, zorder=3, alpha=0.85)
        ax.axvline(vals.mean(), color=C["red"], lw=1.5, ls="--",
                   label=f"Mean: {vals.mean():.1f}", zorder=4)
        ax.legend(fontsize=8)
        ax.set_xlabel(col, fontsize=8)
        ax.set_ylabel("Count", fontsize=8)
        ax.set_title(f"{col} Distribution", fontsize=10,
                     fontweight="bold", color=C["text"], pad=8)
        polish(ax)
        plt.tight_layout()
        return fig2buf(fig)

    # ── Build charts based on what columns exist ───────────────────
    ranking_buf   = chart_ranking()
    subject_buf   = chart_subject_comparison()
    dist_buf      = chart_distribution()
    cat_buf       = chart_category()
    scatter_buf   = chart_scatter()
    pie_buf       = chart_category_pie()
    sec_dist_buf  = chart_secondary_dist()

    # ══════════════════════════════════════════════════════════════
    # SUMMARY STATS
    # ══════════════════════════════════════════════════════════════
    total_records = len(df)
    top_name = fname(df.loc[df[rank_col].idxmax(), name_col]) if rank_col and name_col else "—"
    top_val  = df[rank_col].max() if rank_col else 0
    avg_val  = df[rank_col].mean() if rank_col else 0
    avg_sec  = df[sec_col].mean() if sec_col else None
    avg_pct  = df[pct_col].mean() if pct_col else None

    # ══════════════════════════════════════════════════════════════
    # COVER PAGE
    # ══════════════════════════════════════════════════════════════
    from reportlab.platypus import KeepTogether
    from datetime import date

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm
    )
    W = A4[0] - 40*mm

    class Cover(Flowable):
        def __init__(self):
            super().__init__()
            self.width  = W
            self.height = 90

        def draw(self):
            c = self.canv
            # Background gradient strip
            c.setFillColor(hx(C["navy"]))
            c.roundRect(0, 0, self.width, self.height, 8, fill=1, stroke=0)
            # Accent bar
            c.setFillColor(hx(C["indigo"]))
            c.rect(0, 0, 5, self.height, fill=1, stroke=0)
            # Title
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 18)
            label = dataset_label[:45]
            c.drawString(18, 62, label)
            # Subtitle
            c.setFont("Helvetica", 10)
            c.setFillColor(hx(C["border"]))
            c.drawString(18, 46, "Comprehensive Analytics Report")
            # Meta pills
            c.setFont("Helvetica", 8)
            meta = [
                ("RECORDS", str(total_records)),
                ("COLUMNS", str(len(all_cols))),
                ("GENERATED", date.today().strftime("%d %b %Y")),
            ]
            x = 18
            for label2, val in meta:
                c.setFillColor(hx(C["indigo"]))
                c.roundRect(x, 14, 60, 20, 3, fill=1, stroke=0)
                c.setFillColor(colors.white)
                c.setFont("Helvetica-Bold", 6)
                c.drawString(x+5, 27, label2)
                c.setFont("Helvetica-Bold", 9)
                c.drawString(x+5, 17, val)
                x += 68

    story = []
    story.append(Cover())
    story.append(SP(10))

    # ── Section counter ────────────────────────────────────────────
    sec = [0]
    def next_sec(title, color=None):
        sec[0] += 1
        return SectionHeader(sec[0], title, color)

    # ══════════════════════════════════════════════════════════════
    # SECTION 1: EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════
    story.append(next_sec("Executive Summary"))
    story.append(SP(8))

    # KPI cards — only for columns that actually exist
    kpi_cards = []
    kpi_cards.append(InsightCard("📊","Total Records", str(total_records),
                                  f"{len(all_cols)} columns", C["indigo"]))
    if rank_col:
        kpi_cards.append(InsightCard("⭐", f"Avg {rank_col}",
                                      f"{avg_val:.1f}",
                                      f"{df[rank_col].min():.0f}–{df[rank_col].max():.0f}",
                                      C["blue"]))
        kpi_cards.append(InsightCard("🏆","Top", top_name,
                                      f"{rank_col}: {top_val:.1f}", C["green"]))
    if pct_col:
        kpi_cards.append(InsightCard("📈", f"Avg {pct_col}",
                                      f"{avg_pct:.1f}",
                                      f"Max: {df[pct_col].max():.1f}", C["violet"]))
    if sec_col:
        kpi_cards.append(InsightCard("📋", f"Avg {sec_col}",
                                      f"{avg_sec:.1f}",
                                      f"Max: {df[sec_col].max():.0f}", C["teal"]))

    # Lay KPI cards in a row
    if kpi_cards:
        card_w = 38*mm + 3*mm
        n_per_row = min(4, len(kpi_cards))
        kpi_table_data = [kpi_cards[:n_per_row]]
        col_widths = [card_w] * n_per_row
        kpi_table = Table(kpi_table_data, colWidths=col_widths)
        kpi_table.setStyle(TableStyle([
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),2),
            ("RIGHTPADDING",(0,0),(-1,-1),2),
        ]))
        story.append(kpi_table)
        story.append(SP(8))

    # Summary paragraph
    summary_parts = [f"This report analyzes <b>{total_records} records</b> across "
                     f"<b>{len(all_cols)} columns</b> from the <i>{dataset_label}</i> dataset. "]
    if rank_col:
        summary_parts.append(f"The average {rank_col} is <b>{avg_val:.1f}</b> "
                              f"(range: {df[rank_col].min():.0f}–{df[rank_col].max():.0f}). ")
    if pct_col:
        summary_parts.append(f"Average {pct_col} is <b>{avg_pct:.1f}</b>. ")
    if sec_col:
        summary_parts.append(f"Average {sec_col} is <b>{avg_sec:.1f}</b>. ")
    if name_col and rank_col:
        summary_parts.append(f"Top performer: <b>{top_name}</b> with "
                              f"{rank_col} of <b>{top_val:.1f}</b>. ")
    if insights:
        summary_parts.append(insights[:500])
    story.append(Paragraph("".join(summary_parts), BODY))
    story.append(SP(4))

    # ══════════════════════════════════════════════════════════════
    # DYNAMIC SECTIONS — only add what makes sense for this data
    # ══════════════════════════════════════════════════════════════

    fig_num = [0]
    def fig_label(caption):
        fig_num[0] += 1
        return f"Fig {fig_num[0]} — {caption}"

    def add_img_section(section_title, buf, caption, desc="", color=None):
        if buf is None: return
        story.append(HR())
        story.append(next_sec(section_title, color))
        story.append(SP(8))
        if desc:
            story.append(Paragraph(desc, SMALL))
            story.append(SP(4))
        img = Image(buf, width=W, height=W*0.45)
        story.append(img)
        story.append(Paragraph(fig_label(caption), CAP))

    # Section: Ranking
    if ranking_buf:
        add_img_section(
            f"{rank_col} Ranking",
            ranking_buf,
            f"Records ranked by {rank_col} — green=top 25%, amber=mid, red=bottom 25%",
            f"Records sorted by {rank_col} from highest to lowest. "
            f"Dashed line shows the average ({avg_val:.1f})."
        )

    # Section: Subject/Multi-column comparison (only if 3+ similar numeric cols)
    if subject_buf and len(subject_cols) >= 3:
        col_names = ", ".join(subject_cols[:8])
        add_img_section(
            "Column-wise Average Comparison",
            subject_buf,
            f"Average values across: {col_names}",
            f"Comparison of average values across {len(subject_cols)} related columns: {col_names}.",
            C["teal"]
        )

    # Section: Distribution
    if dist_buf:
        add_img_section(
            f"{rank_col} Distribution",
            dist_buf,
            f"Distribution of {rank_col} values",
            f"Histogram showing how {rank_col} values are spread across all records. "
            f"Mean ({avg_val:.1f}) and median ({df[rank_col].median():.1f}) marked.",
            C["violet"]
        )

    # Section: Category breakdown
    if cat_buf and cat_col:
        add_img_section(
            f"Breakdown by {cat_col}",
            cat_buf,
            f"Average {rank_col} by {cat_col}",
            f"Average {rank_col} grouped by {cat_col}. "
            f"Highest: {df.groupby(cat_col)[rank_col].mean().idxmax()}.",
            C["amber"]
        )

    # Section: Pie chart for category distribution
    if pie_buf and cat_col and df[cat_col].nunique() <= 10:
        story.append(HR())
        story.append(next_sec(f"{cat_col} Distribution", C["teal"]))
        story.append(SP(8))
        img = Image(pie_buf, width=W*0.65, height=W*0.38)
        # Center it
        t = Table([[img]], colWidths=[W])
        t.setStyle(TableStyle([("ALIGN",(0,0),(0,0),"CENTER")]))
        story.append(t)
        story.append(Paragraph(fig_label(f"Distribution of records by {cat_col}"), CAP))

    # Section: Secondary metric distribution
    if sec_dist_buf and (sec_col or pct_col):
        col_used = pct_col or sec_col
        add_img_section(
            f"{col_used} Distribution",
            sec_dist_buf,
            f"Distribution of {col_used}",
            f"Distribution of {col_used} values across all records.",
            C["blue"]
        )

    # Section: Scatter plot
    if scatter_buf and sec_col and rank_col:
        add_img_section(
            f"{sec_col} vs {rank_col}",
            scatter_buf,
            f"{sec_col} vs {rank_col} — dot colour = performance tier",
            f"Relationship between {sec_col} and {rank_col}. "
            f"Correlation: {df[[sec_col,rank_col]].corr().iloc[0,1]:.2f}.",
            C["indigo"]
        )

    # ══════════════════════════════════════════════════════════════
    # KEY INSIGHTS SECTION
    # ══════════════════════════════════════════════════════════════
    story.append(HR())
    story.append(next_sec("Key Insights & Statistics", C["navy"]))
    story.append(SP(8))

    # Build insight bullets from actual data
    insight_bullets = []
    if rank_col:
        gap = df[rank_col].max() - df[rank_col].min()
        insight_bullets.append(f"<b>{rank_col} Range:</b> {gap:.0f} spread between "
                                f"highest ({df[rank_col].max():.1f}) and lowest ({df[rank_col].min():.1f}).")
        std = df[rank_col].std()
        insight_bullets.append(f"<b>Std Deviation ({rank_col}):</b> {std:.1f} — "
                                f"{'high variability' if std > avg_val*0.2 else 'relatively consistent'} across records.")
    if pct_col:
        above_avg = (df[pct_col] >= df[pct_col].mean()).sum()
        insight_bullets.append(f"<b>{pct_col}:</b> {above_avg} of {total_records} records "
                                f"are at or above average ({df[pct_col].mean():.1f}).")
    if sec_col:
        insight_bullets.append(f"<b>{sec_col}:</b> Average is {avg_sec:.1f}, "
                                f"ranging from {df[sec_col].min():.0f} to {df[sec_col].max():.0f}.")
    if cat_col and rank_col:
        best_cat = df.groupby(cat_col)[rank_col].mean().idxmax()
        best_avg = df.groupby(cat_col)[rank_col].mean().max()
        insight_bullets.append(f"<b>Best {cat_col}:</b> {best_cat} has highest "
                                f"average {rank_col} ({best_avg:.1f}).")
    if subject_cols and len(subject_cols) >= 2:
        best_subj = max(subject_cols, key=lambda c: df[c].mean())
        weak_subj = min(subject_cols, key=lambda c: df[c].mean())
        insight_bullets.append(f"<b>Strongest column:</b> {best_subj} "
                                f"(avg {df[best_subj].mean():.1f}). "
                                f"<b>Weakest:</b> {weak_subj} (avg {df[weak_subj].mean():.1f}).")

    for bullet in insight_bullets:
        story.append(Paragraph(f"• {bullet}", BODY))
    story.append(SP(4))

    # ══════════════════════════════════════════════════════════════
    # DATA TABLE
    # ══════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(next_sec("Full Data Table", C["navy"]))
    story.append(SP(6))

    # Choose columns to show — name first, then key metrics, then others (up to 8 cols)
    show_cols = []
    if name_col: show_cols.append(name_col)
    for c in [rank_col, pct_col, sec_col]:
        if c and c not in show_cols: show_cols.append(c)
    # Add subject cols
    for c in subject_cols:
        if c not in show_cols: show_cols.append(c)
    # Add any remaining numeric cols
    for c in num_cols:
        if c not in show_cols: show_cols.append(c)
    # Add cat col
    if cat_col and cat_col not in show_cols: show_cols.append(cat_col)
    # Limit to 9 cols for readability
    show_cols = show_cols[:9]

    # Sort by rank_col descending
    if rank_col:
        disp_df = df.sort_values(rank_col, ascending=False)
    else:
        disp_df = df

    n_rows = min(50, len(disp_df))
    story.append(Paragraph(
        f"{n_rows} record(s) — sorted by {rank_col or 'default'}.", SMALL))
    story.append(SP(4))

    col_w = W / len(show_cols)
    tdata = [[Paragraph(c, TH) for c in show_cols]]
    for _, row in disp_df[show_cols].head(n_rows).iterrows():
        tdata.append([Paragraph(str(row[c])[:18], TC) for c in show_cols])

    tbl = Table(tdata, colWidths=[col_w]*len(show_cols), repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), hx(C["navy"])),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, hx(C["bg"])]),
        ("GRID",(0,0),(-1,-1),0.3, hx(C["border"])),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, hx(C["bg"])]),
    ]))
    story.append(tbl)

    # ── Footer note ────────────────────────────────────────────────
    story.append(SP(12))
    story.append(HR())
    story.append(Paragraph(
        f"Generated by <b>RAG Platform</b> · {date.today().strftime('%d %B %Y')} · CONFIDENTIAL",
        PS("ft", fontSize=7, textColor=hx(C["muted"]), alignment=TA_CENTER)
    ))

    # ── Build ──────────────────────────────────────────────────────
    doc.build(story)
    return out_path