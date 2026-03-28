import json
import os
import re
from database import DatabaseManager
from ingestion.vector_store import VectorStore
from llm_client import LLMClient
from memory import ConversationMemory
from query.planner import QueryPlanner, QueryPlan, is_raw_sql
from query.intent import classify_intent, get_intent_label
from query.agent_prompts import get_prompt, _is_followup
# visualizer and pdf_generator are lazy-loaded only when needed
from utils.logger import get_logger

logger = get_logger(__name__)

_TABULAR_TYPES  = {"csv", "json_array"}
_RAG_ONLY_TYPES = {"pdf", "txt", "json"}

# ─────────────────────────────────────────────
# Greeting Detection
# ─────────────────────────────────────────────

_GREETING_PATTERNS = [
    r"^(hi|hello|hey|hiya|howdy|sup|what'?s up|yo)\b",
    r"^good\s*(morning|afternoon|evening|night|day)\b",
    r"^how are you\b",
    r"^how('?s| is) it going\b",
    r"^how('?re| are) you (doing|going)?\b",
    r"^what('?s| is) your name\b",
    r"^who are you\b",
    r"^are you (a )?(bot|ai|robot|assistant|chatbot)\b",
    r"^(nice|good|great|awesome|cool) (to meet|meeting) you\b",
    r"^(thanks|thank you|thx|ty)\b",
    r"^(bye|goodbye|see you|cya|later|take care)\b",
    r"^(ok|okay|got it|understood|sure|alright)\s*[.!]?\s*$",
    r"^(yes|no|yeah|nope|yep|nah)\s*[.!]?\s*$",
    r"^help\s*$",
    r"^(what can you do|what do you do|what are you capable of)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _GREETING_PATTERNS]


def is_greeting(text: str) -> bool:
    stripped = text.strip().rstrip("!?.").strip()
    return any(p.match(stripped) for p in _COMPILED)


class QueryExecutor:

    def __init__(self, llm, db, vector_store, memory):
        self.llm          = llm
        self.db           = db
        self.vector_store = vector_store
        self.memory       = memory
        self.planner      = QueryPlanner(llm)
        # workspace_id -> last generated pdf_path
        self.workspace_pdf_cache: dict = {}
        # Temporary storage for page sources during answer generation
        self._last_sources: list = []

    def execute(self, question: str, index_id: str) -> dict:

        # ── Greeting first ────────────────────────────────────────────────
        if is_greeting(question):
            return self._run_greeting(question, index_id)

        # ── Load metadata ─────────────────────────────────────────────────
        try:
            metadata = self.vector_store.load_metadata(index_id)
        except FileNotFoundError:
            return {"answer": f"Index '{index_id}' not found. Please ingest a file first."}

        file_type = metadata.get("file_type", "")
        sql_table = metadata.get("sql_table")

        # ── Classify intent ───────────────────────────────────────────────
        intent = classify_intent(question)

        logger.info(
            f"Executing query | file_type={file_type} | intent={intent} | "
            f"q={question[:80]}"
        )

        # ── Route ─────────────────────────────────────────────────────────
        # Email intents work for ALL file types — check before file_type branching
        if intent == "send_email":
            result = self._run_send_email(question, index_id, sql_table, metadata)
        elif intent == "generate_email":
            result = self._run_generate_email(question, index_id, sql_table, metadata)
        elif intent == "send_report_email":
            result = self._run_send_report_email(question, index_id, sql_table, metadata)

        elif file_type in _TABULAR_TYPES:
            if intent == "export_pdf":
                result = self._run_pdf_report(question, index_id, sql_table)
            elif intent == "visualize":
                result = self._run_visualization(question, index_id, sql_table)
            elif intent in ("generate", "transform", "action"):
                result = self._run_agent(question, index_id, intent, sql_table, file_type)
            elif is_raw_sql(question):
                result = self._run_raw_sql(question, sql_table)
            else:
                schema = self.db.get_table_schema(sql_table) if sql_table else None
                plan: QueryPlan = self.planner.plan(question, sql_table, schema)
                if plan.requires_sql and plan.sql_query:
                    result = self._run_planned_sql(question, plan, index_id, intent)
                else:
                    result = self._run_agent(question, index_id, intent, sql_table, file_type)

        elif file_type in _RAG_ONLY_TYPES:
            if intent == "visualize":
                result = {
                    "answer": "📊 Chart analysis works best with CSV or JSON data files. "
                              "This is a text document — I can give you a written analysis instead. Just ask!",
                    "query_type": "rag",
                    "intent": "visualize",
                }
            else:
                result = self._run_agent(question, index_id, intent)
        else:
            result = self._run_agent(question, index_id, intent)

        # ── Attach intent label ───────────────────────────────────────────
        result["intent"]       = result.get("intent", intent)
        result["intent_label"] = get_intent_label(result["intent"])

        # Don't save send_email to memory here — the "Sending..." text is not
        # the real answer. Node.js sends the email and returns the actual result.
        # Memory for email is updated separately if needed.
        skip_memory_types = ("error", "send_email")
        if result.get("query_type") not in skip_memory_types:
            self.memory.add(index_id, question, result["answer"])

        return result

    # ─────────────────────────────────────────────────────────────────────
    # Greeting
    # ─────────────────────────────────────────────────────────────────────

    def _run_greeting(self, question: str, index_id: str) -> dict:
        history_text = self.memory.format_for_prompt(index_id)
        prompt = f"""{history_text}

User message: {question}

You are a friendly AI assistant inside RAG Platform — a document intelligence tool.
Reply naturally and warmly. Keep it short (1-3 sentences).
If asked what you can do, mention: answering questions, writing emails/letters/reports,
analyzing data, generating charts and visualizations, and transforming document content.
Do NOT use markdown or bullet points. Plain conversational text only.
"""
        try:
            answer = self.llm.generate(prompt)
            self.memory.add(index_id, question, answer)
            return {"answer": answer.strip(), "query_type": "greeting", "intent": "greeting", "intent_label": "💬 Chat"}
        except Exception:
            return {"answer": "Hello! 👋 I'm your RAG AI agent. Upload a document and I can answer questions, write emails, analyze data, generate charts, and more!", "query_type": "greeting", "intent": "greeting", "intent_label": "💬 Chat"}

    # ─────────────────────────────────────────────────────────────────────
    # Raw SQL
    # ─────────────────────────────────────────────────────────────────────

    def _sanitize_sql(self, sql, sql_table, schema=None):
        import re as _re
        if not sql or not sql_table:
            return sql
        for wrong in ["transactions", "your_table", "properties", "records"]:
            sql = _re.sub(r"\b" + wrong + r"\b", sql_table, sql, flags=_re.IGNORECASE)
        sql = _re.sub(
            r"FROM\s+\"?" + _re.escape(sql_table) + r"\"?",
            'FROM "' + sql_table + '"',
            sql, flags=_re.IGNORECASE
        )
        if schema:
            for col in schema:
                real = col["name"]
                if " " not in real and "/" not in real:
                    continue
                underscore = real.replace(" ", "_").replace("/", "_")
                if underscore in sql:
                    sql = sql.replace(underscore, '"' + real + '"')
        return sql

    def _run_raw_sql(self, sql: str, sql_table) -> dict:
        if not sql_table:
            return {"answer": "This file does not support SQL queries.", "query_type": "error"}
        try:
            schema    = self.db.get_table_schema(sql_table) if sql_table else None
            corrected = self._sanitize_sql(sql, sql_table, schema)
            df      = self.db.run_query(corrected)
            results = df.to_dict(orient="records")
            answer  = f"Query returned **{len(results)} record(s)**."
            if results:
                answer += f"\n\n```\n{json.dumps(results[:5], indent=2)}\n```"
                if len(results) > 5:
                    answer += f"\n\n*Showing first 5 of {len(results)} records.*"
            return {"answer": answer, "query_type": "sql_raw", "results": results, "row_count": len(results)}
        except Exception as e:
            return {"answer": f"SQL error: {str(e)}\n\nTip: actual table name is `{sql_table}`.", "query_type": "error"}

    # ─────────────────────────────────────────────────────────────────────
    # Planned SQL
    # ─────────────────────────────────────────────────────────────────────

    def _run_planned_sql(self, question: str, plan: QueryPlan, index_id: str, intent: str = "answer") -> dict:
        try:
            tbl = re.search(r'FROM\s+"?(\w+)"?', plan.sql_query or "", re.IGNORECASE)
            sql_table = tbl.group(1) if tbl else None
            schema    = self.db.get_table_schema(sql_table) if sql_table else None
            clean_sql = self._sanitize_sql(plan.sql_query, sql_table or "", schema)
            df = self.db.run_query(clean_sql)
        except Exception as e:
            # SQL failed — fall back to RAG agent as retry
            logger.warning(f"[Retry] SQL failed: {e} — retrying with RAG")
            rag_context = self._get_rag_context(question, index_id)
            if rag_context:
                history_text = self.memory.format_for_prompt(index_id)
                fallback_prompt = get_prompt("answer", question, rag_context, history_text)
                try:
                    fallback_answer = self.llm.generate(fallback_prompt)
                    return {
                        "answer":     fallback_answer,
                        "query_type": "rag",
                        "intent":     intent,
                        "retried":    True,
                    }
                except Exception:
                    pass
            return {"answer": f"SQL error: {str(e)}", "query_type": "error"}

        results = df.to_dict(orient="records")
        total   = len(results)

        if plan.is_aggregate:
            value = df.iloc[0, 0] if not df.empty else "No result"
            return {"answer": f"The result is: **{value}**", "query_type": "sql_aggregate", "row_count": total}

        top          = results[:10]
        history_text = self.memory.format_for_prompt(index_id)
        context      = json.dumps(top, indent=2)
        prompt       = get_prompt(intent, question, context, history_text)

        try:
            answer = self.llm.generate(prompt)
            return {"answer": answer, "query_type": "sql_natural", "row_count": total, "results": top}
        except Exception as e:
            return {"answer": f"Found {total} records. LLM error: {e}", "query_type": "sql_natural", "row_count": total}

    # ─────────────────────────────────────────────────────────────────────
    # Visualization — charts + KPIs + insights + PDF
    # ─────────────────────────────────────────────────────────────────────

    def _run_pdf_report(self, question: str, index_id: str, sql_table: str) -> dict:
        """Generate professional analytics PDF and return download token."""
        if not sql_table:
            return {"answer": "No tabular data found. Please upload a CSV or JSON file first.", "query_type": "error"}
        try:
            df_full = self.db.run_query(f"SELECT * FROM {sql_table}")
        except Exception as e:
            return {"answer": f"Failed to load data: {str(e)}", "query_type": "error"}
        if df_full.empty:
            return {"answer": "The file appears to be empty.", "query_type": "error"}

        # ── Detect filter from question ────────────────────────────
        # e.g. "report for Manish", "analysis of Engineering dept"
        df     = df_full.copy()
        filter_info = None
        str_cols = df.select_dtypes(include="object").columns.tolist()

        q_lower = question.lower()
        for col in str_cols:
            for val in df[col].dropna().unique():
                if str(val).lower() in q_lower:
                    df = df[df[col].str.lower() == str(val).lower()]
                    filter_info = {"field": col, "value": str(val)}
                    logger.info(f"PDF filter: {col}={val}, rows={len(df)}")
                    break
            if filter_info:
                break

        if df.empty:
            df = df_full  # fallback to full if filter matched nothing

        # ── Get filename / label ───────────────────────────────────
        try:
            metadata  = self.vector_store.load_metadata(index_id)
            filename  = (metadata.get("filename") or metadata.get("file_name")
                         or metadata.get("original_filename") or "dataset.csv")
            base_name = os.path.splitext(filename)[0].replace("_"," ").replace("-"," ").title()
        except Exception:
            filename  = "dataset.csv"
            base_name = "Data Analytics"

        if filter_info:
            dataset_label = f"{filter_info['value'].title()} — {base_name}"
        else:
            dataset_label = base_name

        # ── AI insights ────────────────────────────────────────────
        try:
            num_cols = df.select_dtypes(include="number").columns.tolist()
            sample   = df.head(5).to_dict(orient="records")
            context  = (f"filter: {filter_info}" if filter_info
                        else f"{len(df)} total records")
            prompt   = (
                f"Write a 3-sentence professional executive summary ({context}).\n"
                f"Columns: {list(df.columns)}\n"
                f"Sample data: {json.dumps(sample, default=str)}\n"
                f"Stats: {df[num_cols].describe().round(1).to_dict() if num_cols else {}}\n"
                f"Be specific with real numbers. No bullet points. Flowing prose only."
            )
            insights = self.llm.generate(prompt).strip()
        except Exception:
            insights = ""

        # ── Generate PDF ───────────────────────────────────────────
        try:
            from pdf_generator import generate_pdf
            pdf_path = generate_pdf(
                df, insights,
                dataset_label=dataset_label,
                filename=filename,
                filter_info=filter_info
            )
            logger.info(f"PDF generated: {pdf_path}  filter={filter_info}")
            return {
                "answer":     f"Your **{dataset_label}** report is ready — click **⬇ Download PDF** below.",
                "query_type": "pdf_report",
                "pdf_path":   pdf_path,
                "intent":     "export_pdf",
            }
        except Exception as e:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
            return {"answer": f"PDF generation failed: {str(e)}", "query_type": "error"}


    # ─────────────────────────────────────────────────────────────────────
    # Send Email
    # ─────────────────────────────────────────────────────────────────────

    def _run_generate_email(self, question: str, index_id: str, sql_table, metadata: dict) -> dict:
        """
        Draft an email and show it in chat — do NOT send.
        Used when user says: write/type/draft/compose an email.
        """
        filename  = metadata.get("filename", "dataset.csv")
        base_name = os.path.splitext(filename)[0].replace("_"," ").replace("-"," ").title()
        q_lower   = question.lower()

        # Find matching person in data
        context = ""
        if sql_table:
            try:
                df       = self.db.run_query(f"SELECT * FROM {sql_table}")
                str_cols = df.select_dtypes(include="object").columns.tolist()
                matched_row = None

                # Direct name match in question
                for col in str_cols:
                    for val in df[col].dropna().unique():
                        if str(val).lower() in q_lower:
                            rows = df[df[col].str.lower() == str(val).lower()]
                            if not rows.empty:
                                matched_row = rows.iloc[0]
                            break
                    if matched_row is not None:
                        break

                # Pronoun fallback — look in memory
                if matched_row is None:
                    resolved_name = self._resolve_person_from_memory(question, index_id, df)
                    if resolved_name:
                        for col in str_cols:
                            rows = df[df[col].str.lower() == resolved_name.lower()]
                            if not rows.empty:
                                matched_row = rows.iloc[0]
                                break

                if matched_row is not None:
                    context = f"\nEmployee data: {matched_row.to_dict()}"
                else:
                    context = f"\nDataset: {len(df)} records from {base_name}"
            except Exception:
                pass

        prompt = (
            f"Draft a professional email based on this request.\n"
            f"Request: {question}\n{context}\n"
            f"Format:\n"
            f"Subject: <subject line>\n\n"
            f"<email body — 3-5 sentences, professional tone, no markdown>\n\n"
            f"Best regards,\n[Your Name]"
        )
        try:
            draft = self.llm.generate(prompt).strip()
        except Exception:
            draft = f"Subject: {base_name} — Notification\n\nDear Team,\n\nThis is an automated notification from RAG Platform.\n\nBest regards,\n[Your Name]"

        # Strip AI disclaimer lines the LLM sometimes adds
        clean_lines = []
        for line in draft.split("\n"):
            low = line.lower().strip()
            if any(phrase in low for phrase in [
                "please note:", "as an ai", "unable to directly send",
                "copy and send", "i am unable to", "i cannot send",
                "language model", "i don't have the ability"
            ]):
                continue
            clean_lines.append(line)
        draft = "\n".join(clean_lines).strip()

        answer = (
            f"Here is the drafted email:\n\n"
            f"---\n{draft}\n---\n\n"
            f"*Say **send this email to [email]** to actually send it.*"
        )
        return {"answer": answer, "query_type": "generate_email", "intent": "generate_email"}

    def _run_send_report_email(self, question: str, index_id: str, sql_table, metadata: dict) -> dict:
        """
        Send email with content depending on file type:
        - CSV/JSON → attach generated PDF analytics report
        - PDF/TXT  → send the last RAG text response as email body
        Always works for all file types.
        """
        filename  = metadata.get("filename", "untitled")
        file_type = metadata.get("file_type", "")
        # Clean up filename for use as document title
        base_name = os.path.splitext(filename)[0].replace("_"," ").replace("-"," ").title()
        q_lower   = question.lower()

        # ── Determine if PDF attachment is applicable ─────────────────────
        # Only CSV/JSON have PDF analytics reports
        _TABULAR = {"csv", "json_array", "json"}
        can_have_pdf = file_type in _TABULAR
        pdf_path     = self.workspace_pdf_cache.get(index_id) if can_have_pdf else None
        has_pdf      = bool(pdf_path and os.path.exists(pdf_path))

        # ── For PDF/TXT: get last RAG answer from memory ──────────────────
        last_rag_answer = ""
        if not can_have_pdf:
            history = self.memory.get(index_id)
            # Find the last assistant message that is a real content response
            for entry in reversed(history):
                if entry.get("role") == "assistant":
                    text = entry.get("content","").strip()
                    # Skip short system-like messages
                    if len(text) > 80 and "sending" not in text.lower():
                        last_rag_answer = text
                        break

        # ── Load data for recipient lookup (CSV/JSON only) ────────────────
        df = None
        if sql_table:
            try:
                df = self.db.run_query(f'SELECT * FROM "{sql_table}"')
            except Exception:
                pass

        email_col  = None
        filter_row = None
        if df is not None:
            email_col = next((c for c in df.columns if "email" in c.lower()), None)
            str_cols  = df.select_dtypes(include="object").columns.tolist()
            for col in str_cols:
                for val in df[col].dropna().unique():
                    if str(val).lower() in q_lower:
                        matched = df[df[col].str.lower() == str(val).lower()]
                        if not matched.empty:
                            filter_row = matched.iloc[0]
                        break
                if filter_row is not None:
                    break
            if filter_row is None:
                resolved = self._resolve_person_from_memory(question, index_id, df)
                if resolved:
                    for col in str_cols:
                        matched = df[df[col].str.lower() == resolved.lower()]
                        if not matched.empty:
                            filter_row = matched.iloc[0]
                            break

        # ── Extract email address from question ───────────────────────────
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        emails_in_q   = re.findall(email_pattern, question)
        to_email      = emails_in_q[0] if emails_in_q else None

        if not to_email and filter_row is not None and email_col:
            raw = str(filter_row.get(email_col, "")).strip()
            if "@" in raw:
                to_email = raw

        if not to_email:
            return {
                "answer": (
                    "Please specify who to send this to. Examples:\n"
                    "- *send this report to avinash@gmail.com*\n"
                    "- *email this to hr@company.com*"
                ),
                "query_type": "send_report_email",
            }

        if "@" not in str(to_email):
            return {
                "answer": (
                    f"⚠️ Invalid email address: `{to_email}`\n"
                    f"Please provide it directly: *send this to avinash@gmail.com*"
                ),
                "query_type": "send_report_email",
            }

        # ── Resolve recipient name ────────────────────────────────────────
        # For PDF/TXT: use email prefix as name (e.g. avinash from avinash@gmail.com)
        if filter_row is not None:
            name_key       = next((c for c in filter_row.index if "name" in c.lower()), None)
            recipient_name = str(filter_row[name_key]).strip() if name_key else to_email.split("@")[0].title()
        else:
            recipient_name = to_email.split("@")[0].replace(".", " ").replace("_", " ").title()

        # ── Build subject and body based on file type ─────────────────────
        if can_have_pdf and has_pdf:
            # CSV/JSON with PDF attached
            subject = f"{base_name} — Analytics Report"
            body    = (
                f"Dear {recipient_name},\n\n"
                f"Please find the {base_name} analytics report attached to this email.\n\n"
                f"The report includes key metrics, performance charts, data distribution "
                f"analysis, and a complete data table — all generated from the latest dataset.\n\n"
                f"Best regards,\nRAG Platform"
            )

        elif can_have_pdf and not has_pdf:
            # CSV/JSON but no PDF generated yet
            subject = f"{base_name} — Summary"
            body    = (
                f"Dear {recipient_name},\n\n"
                f"Here is a summary of the {base_name} dataset.\n\n"
                f"To include the full analytics PDF report, first say:\n"
                f"'generate analytics report' — then send this email again.\n\n"
                f"Best regards,\nRAG Platform"
            )

        elif last_rag_answer:
            # PDF/TXT — send the actual RAG response as email body
            subject = f"{base_name} — Report"
            body    = (
                f"Dear {recipient_name},\n\n"
                f"Here is the report on {base_name} as requested:\n\n"
                f"{'─' * 50}\n\n"
                f"{last_rag_answer}\n\n"
                f"{'─' * 50}\n\n"
                f"Best regards,\nRAG Platform"
            )

        else:
            # PDF/TXT but no RAG response found
            subject = f"{base_name} — Report"
            body    = (
                f"Dear {recipient_name},\n\n"
                f"Please find the requested information from {base_name} below.\n\n"
                f"To get a detailed report, first ask a question about the document, "
                f"then say 'send this report to [email]'.\n\n"
                f"Best regards,\nRAG Platform"
            )

        payload = {
            "answer":     f"✅ Sending report to **{to_email}**...",
            "query_type": "send_report_email",
            "intent":     "send_report_email",
            "email_mode": "single",
            "recipients": [{"to": to_email, "subject": subject, "body": body}],
        }

        if has_pdf:
            payload["pdf_path"] = pdf_path

        return payload

    def _resolve_person_from_memory(self, question: str, index_id: str, df) -> str | None:
        """
        When question uses pronouns (him/her/them/his), scan recent conversation
        memory to find the last mentioned person name, then look them up in df.
        Returns the matched name value from the data, or None.
        """
        import re as _re
        pronoun_pattern = _re.compile(
            r"\b(him|her|them|his|their|he|she|they)\b", _re.IGNORECASE
        )
        if not pronoun_pattern.search(question):
            return None  # No pronoun — caller handles lookup normally
        if df is None:
            return None

        # Get recent history (last 10 messages)
        history = self.memory.get(index_id)[-10:]
        str_cols = df.select_dtypes(include="object").columns.tolist()

        # Walk history newest-first looking for a name that exists in the data
        for entry in reversed(history):
            text = entry.get("content", "")
            for col in str_cols:
                for val in df[col].dropna().unique():
                    val_str = str(val).strip()
                    if len(val_str) < 2:
                        continue
                    if val_str.lower() in text.lower():
                        return val_str  # Found — return the actual data value
        return None

    def _run_send_email(self, question: str, index_id: str, sql_table, metadata: dict) -> dict:
        """
        Build email payload and return to Node.js for sending via Nodemailer.
        ALWAYS pulls the real email address from CSV data — never hallucinates it.
        """
        filename  = metadata.get("filename", "dataset.csv")
        base_name = os.path.splitext(filename)[0].replace("_"," ").replace("-"," ").title()
        q_lower   = question.lower()

        # ── Load data ─────────────────────────────────────────────────────
        df = None
        if sql_table:
            try:
                df = self.db.run_query(f"SELECT * FROM {sql_table}")
            except Exception:
                pass

        # ── Find email address column ─────────────────────────────────────
        email_col = None
        if df is not None:
            email_col = next((c for c in df.columns if "email" in c.lower()), None)

        # ── Detect person filter from question ────────────────────────────
        filter_row  = None
        filter_info = None
        if df is not None:
            str_cols = df.select_dtypes(include="object").columns.tolist()
            for col in str_cols:
                for val in df[col].dropna().unique():
                    if str(val).lower() in q_lower:
                        matched = df[df[col].str.lower() == str(val).lower()]
                        if not matched.empty:
                            filter_row  = matched.iloc[0]
                            filter_info = {"field": col, "value": str(val)}
                        break
                if filter_row is not None:
                    break

        # ── Pronoun fallback: "send him/her" → look in conversation memory ──
        if filter_row is None and df is not None:
            resolved_name = self._resolve_person_from_memory(question, index_id, df)
            if resolved_name:
                for col in str_cols:
                    matched = df[df[col].str.lower() == resolved_name.lower()]
                    if not matched.empty:
                        filter_row  = matched.iloc[0]
                        filter_info = {"field": col, "value": resolved_name}
                        break

        # ── Detect bulk request ───────────────────────────────────────────
        bulk_keywords = ["all", "everyone", "every", "each", "bulk", "team"]
        is_bulk = any(kw in q_lower for kw in bulk_keywords) and df is not None

        if is_bulk and df is not None:
            if not email_col:
                return {
                    "answer": "No `email` column found in your data. Bulk email requires an email column in the CSV.",
                    "query_type": "send_email",
                }
            name_col = next((c for c in df.columns if "name" in c.lower()), None)
            sal_col  = next((c for c in df.columns if "salary" in c.lower()), None)
            dept_col = next((c for c in df.columns if "dept" in c.lower() or "department" in c.lower()), None)

            subject_tmpl = f"Your {base_name} Summary"
            body_parts   = [f"Hi {{name}},\n\nHere is your personal summary from {base_name}:\n"]
            if name_col:  body_parts.append("Name: {name}")
            if sal_col:   body_parts.append("Salary: {salary}")
            if dept_col:  body_parts.append("Department: {department}")
            body_parts.append("\nThis is an automated report from RAG Platform.")
            body_tmpl = "\n".join(body_parts)

            recipients = []
            for _, row in df.iterrows():
                email_val = str(row.get(email_col, "")).strip()
                if "@" not in email_val:
                    continue
                subj = subject_tmpl
                body = body_tmpl
                for col in df.columns:
                    ph = "{" + str(col) + "}"
                    subj = subj.replace(ph, str(row[col]))
                    body = body.replace(ph, str(row[col]))
                recipients.append({"to": email_val, "subject": subj, "body": body})

            if not recipients:
                return {"answer": "No valid email addresses found in the data.", "query_type": "send_email"}

            return {
                "answer":     f"Sending bulk email to {len(recipients)} recipient(s)...",
                "query_type": "send_email",
                "intent":     "send_email",
                "email_mode": "bulk",
                "recipients": recipients,
            }

        # ── Single email ──────────────────────────────────────────────────
        to_email = None

        # Priority 1: email address typed directly in question
        email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
        emails_in_q   = re.findall(email_pattern, question)
        if emails_in_q:
            to_email = emails_in_q[0]

        # Priority 2: pull from CSV row of matching person — REAL email, not hallucinated
        if not to_email and filter_row is not None and email_col:
            real_email = str(filter_row.get(email_col, "")).strip()
            if "@" in real_email:
                to_email = real_email

        # Priority 3: no email found at all
        if not to_email:
            return {
                "answer": (
                    "I couldn't find an email address for this person.\n\n"
                    "Try one of these:\n"
                    "- *send email to avinash@gmail.com* — type the address directly\n"
                    "- *email all employees* — send to everyone in the CSV"
                ),
                "query_type": "send_email",
            }

        # Priority 4: email found but malformed (missing @) — bad CSV data
        if "@" not in str(to_email):
            return {
                "answer": (
                    f"⚠️ The email address found in the CSV is invalid: `{to_email}`\n\n"
                    f"It appears to be missing the **@** symbol. "
                    f"Please fix the CSV or provide the address directly:\n"
                    f"*send email to avinash@gmail.com with promotion details*"
                ),
                "query_type": "send_email",
            }

        # ── Check memory for a previously drafted email ──────────────────
        # If the user said "write/draft email" before saying "send it",
        # we should reuse that draft instead of regenerating a new email.
        drafted_subj = None
        drafted_body = None
        history = self.memory.get(index_id)

        # Walk history newest-first looking for a generate_email response
        for entry in reversed(history):
            if entry.get("role") != "assistant":
                continue
            text = entry.get("content", "")
            # Look for a drafted email in the response (has Subject: line)
            if "subject:" in text.lower() and len(text) > 100:
                lines = text.split("\n")
                # Extract subject
                for line in lines:
                    if line.lower().startswith("subject:"):
                        drafted_subj = line.replace("Subject:","").replace("subject:","").strip()
                        break
                # Extract body — everything after subject line,
                # strip the "Here is the drafted email" wrapper and "---" separators
                body_lines = []
                in_body = False
                for line in lines:
                    if line.lower().startswith("subject:"):
                        in_body = True
                        continue
                    if in_body:
                        # Stop at the "Say send him this email" instruction line
                        if line.strip().startswith("*Say") or line.strip().startswith("Say **send"):
                            break
                        # Strip markdown separators
                        if line.strip() in ("---", "___", "***"):
                            continue
                        # Strip "Please note: As an AI" disclaimer lines
                        if "please note:" in line.lower() or "as an ai" in line.lower():
                            continue
                        if "unable to directly send" in line.lower():
                            continue
                        if "copy and send" in line.lower():
                            continue
                        body_lines.append(line)
                if body_lines:
                    drafted_body = "\n".join(body_lines).strip()
                if drafted_subj and drafted_body:
                    logger.info("[send_email] Reusing drafted email from memory")
                    break
                else:
                    drafted_subj = None
                    drafted_body = None

        # ── Use draft or generate fresh ───────────────────────────────────
        if drafted_subj and drafted_body:
            subj = drafted_subj
            body = drafted_body
        else:
            # No draft found — generate fresh email with LLM
            context = ""
            if filter_row is not None:
                context = f"\nEmployee data: {filter_row.to_dict()}"
            elif df is not None:
                context = f"\nDataset: {len(df)} records from {base_name}"

            prompt = (
                f"Write a short professional email.\n"
                f"To: {to_email}\n"
                f"Request: {question}\n{context}\n"
                f"Rules:\n"
                f"- First line: 'Subject: <subject>'\n"
                f"- Then blank line\n"
                f"- Then body (3-5 sentences, plain text, no markdown, no [placeholder] brackets)\n"
                f"- Do NOT add any notes or disclaimers about being an AI\n"
                f"- Sign off as: RAG Platform"
            )
            try:
                raw   = self.llm.generate(prompt).strip()
                lines = raw.split("\n")
                subj  = next(
                    (l.replace("Subject:", "").strip()
                     for l in lines if l.lower().startswith("subject:")),
                    f"{base_name} — Your Information"
                )
                body_lines = [l for l in lines if not l.lower().startswith("subject:")]
                # Strip AI disclaimer lines
                body_lines = [
                    l for l in body_lines
                    if "please note:" not in l.lower()
                    and "as an ai" not in l.lower()
                    and "unable to directly send" not in l.lower()
                    and "copy and send" not in l.lower()
                ]
                body = "\n".join(body_lines).strip()
            except Exception:
                subj = f"{base_name} — Information"
                body = f"Hi,\n\nPlease find your requested information below.\n\nRAG Platform"

        return {
            "answer":     f"Sending email to **{to_email}**...",
            "query_type": "send_email",
            "intent":     "send_email",
            "email_mode": "single",
            "recipients": [{"to": to_email, "subject": subj, "body": body}],
        }

    def _run_visualization(self, question: str, index_id: str, sql_table: str) -> dict:
        """
        Full pipeline:
        1. Load ALL rows from SQL into DataFrame
        2. Auto-detect columns → build bar/pie/line/multibar charts
        3. Generate AI insights paragraph
        4. Return viz_data JSON for frontend to render as interactive charts
        """
        if not sql_table:
            return {"answer": "No tabular data found. Please upload a CSV or JSON file.", "query_type": "error"}

        try:
            df = self.db.run_query(f"SELECT * FROM {sql_table}")
        except Exception as e:
            return {"answer": f"Failed to load data: {str(e)}", "query_type": "error"}

        if df.empty:
            return {"answer": "The file appears to be empty.", "query_type": "error"}

        try:
            from query.visualizer import build_visualization
            viz_data = build_visualization(df, question, llm=self.llm)
        except Exception as e:
            logger.error(f"Visualization failed: {e}")
            return {"answer": f"Visualization error: {str(e)}", "query_type": "error"}

        logger.info(
            f"Visualization done | charts={len(viz_data.get('charts', []))} | "
            f"kpis={len(viz_data.get('kpis', []))} | rows={viz_data.get('total_records')}"
        )

        return {
            "answer":     viz_data.get("insights", "Analysis complete."),
            "query_type": "visualization",
            "viz_data":   viz_data,
            "intent":     "visualize",
        }

    # ─────────────────────────────────────────────────────────────────────
    # Agent — RAG retrieval + intent-specific prompt
    # ─────────────────────────────────────────────────────────────────────


    # ─────────────────────────────────────────────────────────────────────
    # Option 3 — Targeted Retry on Bad Answers
    # ─────────────────────────────────────────────────────────────────────

    # Phrases that signal the answer is clearly bad / empty
    _FAILURE_PHRASES = [
        "doesn't cover",
        "does not cover",
        "not covered",
        "not found",
        "no information",
        "no data",
        "i don't know",
        "i do not know",
        "cannot find",
        "could not find",
        "unable to find",
        "not available",
        "not mentioned",
        "not provided",
        "the document does not",
        "the document doesn't",
        "no relevant",
        "no results",
        "i couldn't find",
        "i could not find",
        "context does not",
        "context doesn't",
        "not in the",
    ]

    def _enforce_document_only(self, answer: str, context: str, question: str) -> str:
        """
        Strict mode: if the LLM answered from general knowledge instead of the document,
        block the answer and return the standard "not in document" response.

        Detects general knowledge answers by checking:
        1. Context is empty or very sparse (no relevant chunks found)
        2. Answer doesn't reference the "document" or contain any hedging phrases
        3. Answer is a confident factual statement about general world knowledge
        """
        if not context or len(context.strip()) < 50:
            # No document context was found — LLM must have used general knowledge
            logger.info("[StrictMode] No context found — blocking general knowledge answer")
            return (
                "This question is not covered in the uploaded document. "
                "Please ask questions related to the document content."
            )

        # Check if LLM explicitly said it's using outside knowledge
        answer_lower = answer.lower()
        outside_signals = [
            "to address your question:",
            "while this isn't in the document",
            "though not mentioned in the document",
            "from my general knowledge",
            "based on my training",
            "as a general fact",
            "outside of the document",
            "not in the document, but",
            "the document doesn't mention this, but",
        ]
        if any(signal in answer_lower for signal in outside_signals):
            logger.info("[StrictMode] LLM used outside knowledge — blocking answer")
            return (
                "This question is not covered in the uploaded document. "
                "Please ask questions related to the document content."
            )

        return answer

    def _is_bad_answer(self, answer: str) -> bool:
        """
        Returns True if the answer clearly failed to address the question.
        Only triggers retry for genuinely bad answers — not for valid short answers.
        """
        if not answer or len(answer.strip()) < 10:
            return True
        answer_lower = answer.lower().strip()
        return any(phrase in answer_lower for phrase in self._FAILURE_PHRASES)

    def _get_rag_context_broad(self, question: str, index_id: str) -> str:
        """
        Broader RAG search for retry — fetches more chunks and rephrases
        the question to catch more relevant passages.
        """
        try:
            # Fetch more chunks than normal (top_k * 2)
            chunks, _ = self.vector_store.search(index_id, question, top_k=20)
        except Exception as e:
            logger.warning(f"Broad RAG search failed: {e}")
            return ""
        if not chunks:
            return ""
        return "\n\n".join(f"[Passage {i+1}]\n{c}" for i, c in enumerate(chunks[:10]))

    def _run_agent(self, question: str, index_id: str, intent: str,
                   sql_table: str = None, file_type: str = None) -> dict:
        context      = ""
        history_text = self.memory.format_for_prompt(index_id)
        is_followup  = _is_followup(question)

        if file_type in _TABULAR_TYPES and sql_table:
            try:
                df      = self.db.run_query(f"SELECT * FROM {sql_table} LIMIT 100")
                records = df.to_dict(orient="records")
                context = json.dumps(records, indent=2)
            except Exception as e:
                logger.warning(f"Agent SQL fetch failed, falling back to RAG: {e}")
                context = self._get_rag_context(question, index_id)
        else:
            if is_followup and history_text:
                context = self._get_rag_context_broad(question, index_id)
                if not context:
                    context = self._get_rag_context(question, index_id)
                self._last_sources = []
            else:
                # Use sources-aware search for page citations
                context, sources = self._get_rag_context_with_sources(question, index_id)
                self._last_sources = sources

        # For follow-up questions: even if context is empty, we can answer from history
        if not context and not is_followup:
            return {
                "answer": "I couldn't find relevant information in the document to complete this task.",
                "query_type": "agent",
                "intent": intent,
            }
        if not context:
            context = "(No additional document context — answer from conversation history above)"

        prompt = get_prompt(intent, question, context, history_text)

        query_type_map = {
            "generate":  "agent_generate",
            "analyze":   "agent_analyze",
            "transform": "agent_transform",
            "action":    "agent_action",
            "answer":    "rag",
        }

        try:
            answer = self.llm.generate(prompt)
        except Exception as e:
            logger.error(f"Agent LLM error: {e}")
            return {"answer": f"LLM error: {str(e)}", "query_type": "error"}

        # ── Option 3: Targeted Retry on bad answer ────────────────────────
        if self._is_bad_answer(answer):
            logger.info(f"[Retry] Bad answer detected — retrying with broader context | q={question[:60]}")
            broad_context = self._get_rag_context_broad(question, index_id)
            if broad_context and broad_context != context:
                retry_prompt = get_prompt(intent, question, broad_context, history_text)
                try:
                    retry_answer = self.llm.generate(retry_prompt)
                    # Only use retry if it's actually better
                    if not self._is_bad_answer(retry_answer):
                        logger.info("[Retry] Retry answer is better — using it")
                        answer = retry_answer
                    else:
                        logger.info("[Retry] Retry also bad — keeping original")
                except Exception as e:
                    logger.warning(f"[Retry] Retry LLM call failed: {e}")

        # ── Strict mode: block general knowledge answers ──────────────────
        # If context is empty or very short AND answer sounds factual/confident,
        # the LLM likely used outside knowledge — block it
        answer = self._enforce_document_only(answer, context, question)

        # Append page sources to answer if available
        if hasattr(self, '_last_sources') and self._last_sources:
            source_text = ", ".join(self._last_sources)
            if not self._is_bad_answer(answer):
                answer = f"{answer}\n\n*📄 Source: {source_text}*"
            self._last_sources = []

        return {
            "answer":     answer,
            "query_type": query_type_map.get(intent, "rag"),
            "intent":     intent,
        }

    def _get_rag_context(self, question: str, index_id: str) -> str:
        try:
            chunks, _ = self.vector_store.search(index_id, question)
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return ""
        if not chunks:
            return ""
        # Chunks from PDFs already have [Page N] prefix added by file_handler
        # Just format them clearly for the LLM
        return "\n\n".join(f"[Passage {i+1}]\n{c}" for i, c in enumerate(chunks[:5]))

    def _get_rag_context_with_sources(self, question: str, index_id: str) -> tuple:
        """
        Returns (context_string, sources_list) where sources has page numbers.
        Used when we want to show the user which pages the answer came from.
        """
        try:
            chunks, scores = self.vector_store.search(index_id, question)
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return "", []
        if not chunks:
            return "", []

        # Get page numbers for these chunks
        try:
            pages = self.vector_store.get_chunk_pages(index_id, chunks[:5])
        except Exception:
            pages = [None] * len(chunks[:5])

        # Build context with page info
        parts = []
        sources = []
        for i, (chunk, page) in enumerate(zip(chunks[:5], pages)):
            parts.append(f"[Passage {i+1}]\n{chunk}")
            if page:
                sources.append(f"Page {page}")

        # Deduplicate sources
        seen = set()
        unique_sources = []
        for s in sources:
            if s not in seen:
                seen.add(s)
                unique_sources.append(s)

        return "\n\n".join(parts), unique_sources