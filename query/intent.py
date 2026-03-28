"""
Intent Classifier — detects what the user wants to DO with the document.

Intents:
  greeting       — hi, hello, thanks etc.
  generate_email — draft/write/type/compose an email (show in chat, do NOT send)
  send_email     — actually SEND an email via Nodemailer
  export_pdf     — download analytics PDF report
  visualize      — charts, graphs, dashboard
  generate       — create other content (letter, report, memo, etc.)
  analyze        — derive insights (top/lowest, compare, trend, rank)
  transform      — reformat data (list all, table of, extract all)
  action         — multi-step follow-up (do the same for all)
  answer         — normal Q&A (default fallback)
"""

import re

# ── Draft email (show in chat only — do NOT send) ──────────────────────────────
_GENERATE_EMAIL = [
    r"\b(write|draft|compose|type|create|prepare|craft)\b.{0,50}(email|letter|mail)\b",
]
_GENERATE_EMAIL_RE = [re.compile(p, re.IGNORECASE) for p in _GENERATE_EMAIL]

# ── Send email patterns (actually send via Nodemailer) ─────────────────────────
_SEND_EMAIL = [
    r"\bsend (him|her|them|it|this|the email|this email|mail)\b",
    r"\bsend (email|mail) to\b",
    r"\bsend.{0,30}(his|her|their).{0,10}(mail|email|id)\b",
    r"\b(email|mail)\b.{0,30}\b(him|her|them|all|everyone|team|department)\b",
    r"\bemail (all|every|each)\b",
    r"\b(forward|deliver)\b.{0,30}(email|mail)\b",
    r"\b(send|forward|deliver)\b.{0,20}[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b",
    r"\b(notify|inform)\b.{0,30}(email|mail)\b",
    r"\bemail (report|summary|details|info|data|analysis)\b",
    r"\bemail [A-Za-z]+\b",
]
_SEND_EMAIL_RE = [re.compile(p, re.IGNORECASE) for p in _SEND_EMAIL]

# ── Send Report via Email patterns ────────────────────────────────────────────
# Triggered when user wants to email a previously generated PDF report
_SEND_REPORT_EMAIL = [
    r"\bsend (this |the )?(report|pdf|analysis|file)\b",
    r"\bemail (this |the )?(report|pdf|analysis|file)\b",
    r"\bshare (this |the )?(report|pdf|analysis|file)\b",
    r"\bsend (it|this) (to|via|on)\b",
    r"\bsend.*\b(report|pdf)\b.*(to|for)\b",
]
_SEND_REPORT_EMAIL_RE = [re.compile(p, re.IGNORECASE) for p in _SEND_REPORT_EMAIL]

# ── Export PDF patterns ────────────────────────────────────────────────────────
_EXPORT_PDF = [
    r"\b(download|export|save|generate|create|give me).{0,25}(pdf|report|file)\b",
    r"\b(pdf|report).{0,20}(download|export|save)\b",
    r"\bdownload (it|this|the analysis|analysis)\b",
    r"\b(analytics report|analysis report|data report)\b",
    r"\bgive me (a |the )?(pdf|report|file)\b",
]
_EXPORT_PDF_RE = [re.compile(p, re.IGNORECASE) for p in _EXPORT_PDF]

# ── Visualize patterns ─────────────────────────────────────────────────────────
_VISUALIZE = [
    r"\b(chart|charts|graph|graphs|diagram|diagrams|plot|plots|visuali[sz]e|visualization)\b",
    r"\b(bar chart|pie chart|line chart|line graph|histogram|scatter)\b",
    r"\b(dashboard|analytics|analysis|analyse|analyze)\b",
    r"\b(show me|give me|generate|create|make|draw)\b.{0,30}(chart|graph|diagram|plot|visual)\b",
    r"\b(full analysis|complete analysis|detailed analysis|data analysis|statistical analysis)\b",
    r"\b(performance (report|overview|breakdown|summary))\b",
    r"\b(distribution|breakdown|overview|trends?|pattern)\b",
    r"\b(show (me )?(the )?(data|stats|statistics|numbers|figures))\b",
    r"\b(statistics|stats)\b",
    r"\b(kpi|key (performance|metrics|indicators))\b",
]
_VISUALIZE_RE = [re.compile(p, re.IGNORECASE) for p in _VISUALIZE]

# ── Generate patterns (non-email content) ─────────────────────────────────────
_GENERATE = [
    r"\b(write|draft|compose|type|create|generate|make|prepare|produce|craft|author)\b.{0,40}"
    r"(letter|report|summary|memo|notice|notification|reply|response|"
    r"apology|announcement|proposal|recommendation|review|feedback|note|document|"
    r"certificate|offer|warning|termination|appraisal|invoice|receipt|contract)\b",
    r"\b(format|convert|rewrite|rephrase|simplify|translate)\b",
    r"\b(formal version|professional version|simple version)\b",
    r"\bwrite\b",
    r"\bdraft\b",
    r"\bcompose\b",
]
_GENERATE_RE = [re.compile(p, re.IGNORECASE) for p in _GENERATE]

# ── Analyze patterns ───────────────────────────────────────────────────────────
_ANALYZE = [
    r"\b(highest|lowest|best|worst|top|bottom|most|least|maximum|minimum|max|min)\b",
    r"\b(rank|ranking|ranked|compare|comparison|versus|vs\.?|better|worse)\b",
    r"\b(trend|pattern|insight|analysis|analyze|analyse)\b",
    r"\b(average|mean|median|total|sum|count|how many|percentage|ratio)\b",
    r"\b(who (has|have|is|are) the (best|worst|highest|lowest|most|least))\b",
    r"\b(which (is|are) the (best|worst|highest|lowest|most|least))\b",
    r"\b(performance|performan)\b",
]
_ANALYZE_RE = [re.compile(p, re.IGNORECASE) for p in _ANALYZE]

# ── Transform patterns ─────────────────────────────────────────────────────────
_TRANSFORM = [
    r"\b(list all|show all|give me all|extract all|find all|get all)\b",
    r"\b(table of|make a table|create a table|tabulate)\b",
    r"\b(summarize all|summary of all|overview of all)\b",
    r"\b(extract|pull out|get out)\b.{0,30}(names|emails|dates|numbers|ids|prices|addresses)\b",
    r"\b(all the|every)\b.{0,20}(names|emails|records|entries|rows|items)\b",
    r"\b(bullet points?|numbered list|outline|key points)\b",
    r"\b(study guide|cheat sheet|quick reference|FAQ)\b",
]
_TRANSFORM_RE = [re.compile(p, re.IGNORECASE) for p in _TRANSFORM]

# ── Action patterns ────────────────────────────────────────────────────────────
_ACTION = [
    r"\b(do the same|same for|same thing)\b",
    r"\b(now (do|write|create|generate|draft))\b",
    r"\b(for (all|each|every) (of them|employee|person|record|row|entry))\b",
    r"\b(apply (this|that) to all)\b",
]
_ACTION_RE = [re.compile(p, re.IGNORECASE) for p in _ACTION]

# Direct send target: "send him", "send it", "send this" → always send_email
_DIRECT_SEND_RE = re.compile(
    r"\bsend (him|her|them|it|this|the email|this email)\b", re.IGNORECASE
)


def classify_intent(question: str) -> str:
    """
    Priority order:
    action > send_email > generate_email > export_pdf > visualize > generate > transform > analyze > answer

    Special rule for email:
    - "write/type/draft + email" without a direct send target → generate_email (draft only)
    - "send him/it/this" or "email [name]" → send_email (actually send)
    """
    q = question.strip()

    if any(p.search(q) for p in _ACTION_RE):
        return "action"

    # Report email — user wants to send a previously generated PDF
    if any(p.search(q) for p in _SEND_REPORT_EMAIL_RE):
        return "send_report_email"

    # Email routing — check both patterns first
    is_gen_email  = any(p.search(q) for p in _GENERATE_EMAIL_RE)
    is_send_email = any(p.search(q) for p in _SEND_EMAIL_RE)
    has_direct_send = bool(_DIRECT_SEND_RE.search(q))

    if is_gen_email and not has_direct_send:
        return "generate_email"
    if is_send_email or has_direct_send:
        return "send_email"

    if any(p.search(q) for p in _EXPORT_PDF_RE):
        return "export_pdf"

    if any(p.search(q) for p in _VISUALIZE_RE):
        return "visualize"

    if any(p.search(q) for p in _GENERATE_RE):
        return "generate"

    if any(p.search(q) for p in _TRANSFORM_RE):
        return "transform"

    if any(p.search(q) for p in _ANALYZE_RE):
        return "analyze"

    return "answer"


def get_intent_label(intent: str) -> str:
    """Human-readable label shown in the chat bubble badge."""
    return {
        "visualize":      "📊 Charts",
        "generate":       "✍️ Write",
        "generate_email": "✍️ Draft Email",
        "analyze":        "🔎 Analyze",
        "transform":      "🔄 Extract",
        "action":         "⚡ Action",
        "answer":         "🔍 RAG",
        "greeting":       "💬 Chat",
        "send_email":       "📧 Email Sent",
        "send_report_email": "📧 Report Sent",
        "export_pdf":     "📄 PDF",
    }.get(intent, "🔍 RAG")