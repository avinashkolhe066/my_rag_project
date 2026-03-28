import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import config
from llm_client import LLMClient
from database import DatabaseManager
from memory import ConversationMemory
from workspace import WorkspaceManager
from ingestion.file_handler import parse_file
from ingestion.vector_store import VectorStore
from query.executor import QueryExecutor
from query.executor import is_greeting
from utils.logger import get_logger
from internal_auth import InternalAPIKeyMiddleware
from quiz_generator import QuizGenerator

logger = get_logger(__name__)

# ─────────────────────────────────────────────
# App Initialization
# ─────────────────────────────────────────────

app = FastAPI(
    title="Hybrid RAG API",
    description="Workspace-based RAG system. Each workspace has one file and isolated chat history.",
    version="3.0.0",
)

app.add_middleware(InternalAPIKeyMiddleware)

# ─────────────────────────────────────────────
# Services
# ─────────────────────────────────────────────

llm          = LLMClient()
db           = DatabaseManager()
vector_store = VectorStore()
memory       = ConversationMemory()
workspaces   = WorkspaceManager()
_viz_cache:  dict = {}  # viz data cache
_pdf_cache:       dict = {}  # pdf token → file path
_workspace_pdf:   dict = {}  # workspace_id → last generated pdf_path
executor     = QueryExecutor(llm=llm, db=db, vector_store=vector_store, memory=memory)

logger.info("Hybrid RAG API v3 started")

# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class CreateWorkspaceRequest(BaseModel):
    name: str

class QueryRequest(BaseModel):
    question: str

# ─────────────────────────────────────────────
# Root
# ─────────────────────────────────────────────

@app.get("/", summary="Health check")
def root():
    return {
        "status": "running",
        "version": "3.0.0",
        "llm_backend": config.LLM_BACKEND,
        "supported_formats": ["csv", "json", "pdf", "txt"],
    }

# ─────────────────────────────────────────────
# Workspace Endpoints
# ─────────────────────────────────────────────

@app.post("/workspace", summary="Create a new workspace")
def create_workspace(req: CreateWorkspaceRequest):
    """Create a new empty workspace. Returns workspace_id."""
    workspace = workspaces.create(name=req.name)
    logger.info(f"Workspace created | id={workspace['workspace_id']} | name={req.name}")
    return workspace


@app.get("/workspace", summary="List all workspaces")
def list_workspaces():
    """Returns all workspaces with their details."""
    all_ws = workspaces.list_all()
    return {
        "total": len(all_ws),
        "workspaces": all_ws,
    }


@app.get("/workspace/{workspace_id}", summary="Get workspace details")
def get_workspace(workspace_id: str):
    """Get details of a single workspace including file info and chat history count."""
    ws = workspaces.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    return {
        **ws,
        "history_exchanges": memory.get_exchange_count(ws["index_id"]) if ws["index_id"] else 0,
    }


@app.post("/workspace/{workspace_id}/ingest", summary="Upload a file to a workspace")
async def ingest_to_workspace(workspace_id: str, file: UploadFile = File(...)):
    """
    Upload a file (CSV, JSON, PDF, TXT) to a workspace.
    - If workspace already has a file, the old file is replaced.
    - Old chat history is cleared automatically on file replacement.
    - Use workspace_id = 'auto' to create a new workspace automatically.
    """

    # Auto-create workspace if workspace_id is "auto"
    if workspace_id == "auto":
        ws = workspaces.create(name=file.filename)
        workspace_id = ws["workspace_id"]
        logger.info(f"Auto-created workspace | id={workspace_id}")
    else:
        ws = workspaces.get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    content = await file.read()

    # Parse the file
    try:
        chunks, dataframe, file_type = parse_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Parsing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse the uploaded file.")

    if not chunks:
        raise HTTPException(status_code=400, detail="No content could be extracted from the file.")

    # If workspace already had a file — delete old index + clear history
    if ws.get("index_id"):
        old_index_id = ws["index_id"]
        vector_store.delete(old_index_id)
        memory.clear(old_index_id)
        logger.info(f"Old file replaced | workspace_id={workspace_id} | old_index={old_index_id}")

    # Save to SQLite if tabular
    sql_table = None
    if dataframe is not None:
        sql_table = f"data_{uuid.uuid4().hex}"
        try:
            db.save_dataframe(dataframe, sql_table)
        except Exception as e:
            logger.error(f"SQLite save failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to save tabular data.")

    # Save to vector store
    metadata = {
        "file_type": file_type,
        "sql_table": sql_table,
        "original_filename": file.filename,
    }
    try:
        index_id = vector_store.save(chunks, metadata)
    except Exception as e:
        logger.error(f"Vector store save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to build search index.")

    # Attach file info to workspace
    ws = workspaces.attach_file(
        workspace_id=workspace_id,
        index_id=index_id,
        file_name=file.filename,
        file_type=file_type,
        sql_table=sql_table,
    )

    logger.info(
        f"Ingest complete | workspace_id={workspace_id} | "
        f"file={file.filename} | file_type={file_type} | chunks={len(chunks)}"
    )

    return {
        "message": "File uploaded successfully.",
        "workspace_id": workspace_id,
        "workspace_name": ws["name"],
        "index_id": index_id,
        "file_name": file.filename,
        "file_type": file_type,
        "num_chunks": len(chunks),
        "sql_table": sql_table,
    }


@app.post("/workspace/{workspace_id}/query", summary="Ask a question in a workspace")
def query_workspace(workspace_id: str, req: QueryRequest):
    """
    Ask a question about the file in this workspace.
    Each workspace has completely isolated RAG and chat history.
    Follow-up questions like 'tell me more' work because history is remembered.
    """
    ws = workspaces.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    # Allow greetings even when no file is uploaded yet
    if not ws.get("index_id"):
        if is_greeting(req.question):
            # No index_id yet — use workspace_id as a memory key for the session
            session_id = f"greeting_{workspace_id}"
            result = executor._run_greeting(req.question, session_id)
            memory.add(session_id, req.question, result["answer"])
            result["history_length"] = memory.get_exchange_count(session_id)
            result["workspace_id"] = workspace_id
            result["workspace_name"] = ws["name"]
            return result
        raise HTTPException(
            status_code=400,
            detail="This workspace has no file. Please upload a file before asking document questions.",
        )

    logger.info(
        f"Query | workspace_id={workspace_id} | "
        f"file={ws.get('file_name','unknown')} | question={req.question[:80]}"
    )

    result = executor.execute(question=req.question, index_id=ws["index_id"])
    result["history_length"] = memory.get_exchange_count(ws["index_id"])
    result["workspace_id"] = workspace_id
    result["workspace_name"] = ws["name"]

    return result


@app.delete("/workspace/{workspace_id}", summary="Delete a workspace and all its data")
def delete_workspace(workspace_id: str):
    """
    Deletes the workspace entry, FAISS index, and chat history.
    This action cannot be undone.
    """
    ws = workspaces.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    if ws.get("index_id"):
        vector_store.delete(ws["index_id"])
        memory.clear(ws["index_id"])

    workspaces.delete(workspace_id)
    logger.info(f"Workspace fully deleted | id={workspace_id} | name={ws['name']}")

    return {
        "message": f"Workspace '{ws['name']}' and all its data have been deleted.",
        "workspace_id": workspace_id,
    }



@app.get("/history/{index_id}", summary="Get chat history for an index")
def get_history(index_id: str):
    """Returns all conversation exchanges stored for this index_id."""
    history = memory.get_all(index_id)
    return {"index_id": index_id, "history": history}

@app.delete("/workspace/{workspace_id}/history", summary="Clear chat history for a workspace")
def clear_workspace_history(workspace_id: str):
    """Clears only the chat history. File stays uploaded and ready to query."""
    ws = workspaces.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    if ws.get("index_id"):
        memory.clear(ws["index_id"])

    return {
        "message": f"Chat history cleared for workspace '{ws['name']}'.",
        "workspace_id": workspace_id,
    }


# ─────────────────────────────────────────────
# Legacy Endpoints (backward compatibility)
# ─────────────────────────────────────────────

@app.post("/ingest", summary="[Legacy] Direct ingest without workspace")
async def ingest(file: UploadFile = File(...)):
    """Legacy endpoint. Prefer /workspace/{id}/ingest instead."""
    content = await file.read()
    try:
        chunks, dataframe, file_type = parse_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    sql_table = None
    if dataframe is not None:
        sql_table = f"data_{uuid.uuid4().hex}"
        db.save_dataframe(dataframe, sql_table)

    metadata = {
        "file_type": file_type,
        "sql_table": sql_table,
        "original_filename": file.filename,
    }
    index_id = vector_store.save(chunks, metadata)

    return {
        "message": "File ingested successfully.",
        "index_id": index_id,
        "file_type": file_type,
        "num_chunks": len(chunks),
        "sql_table": sql_table,
    }


@app.post("/query", summary="[Legacy] Direct query without workspace")
def query(req_body: dict):
    """Legacy endpoint. Prefer /workspace/{id}/query instead."""
    question = req_body.get("question", "")
    index_id = req_body.get("index_id", "")
    result = executor.execute(question=question, index_id=index_id)
    result["history_length"] = memory.get_exchange_count(index_id)
    return result




# ─────────────────────────────────────────────
# Streaming Query Endpoint
# ─────────────────────────────────────────────

@app.post("/workspace/{workspace_id}/stream", summary="Stream answer word by word via SSE")
async def stream_workspace(workspace_id: str, req: QueryRequest):
    """
    Streams the answer token by token using Server-Sent Events.
    Handles: greetings (no file needed), RAG, SQL queries.
    """
    import asyncio
    import json as _json

    ws = workspaces.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    async def event_generator():
        try:
            # ── Case 1: No file uploaded ──────────────────────────────────
            if not ws.get("index_id"):
                if is_greeting(req.question):
                    session_id = f"greeting_{workspace_id}"
                    result = executor._run_greeting(req.question, session_id)
                else:
                    yield "data: __ERROR__This workspace has no file. Please upload a file first.\n\n"
                    yield "data: __DONE__\n\n"
                    return

            # ── Case 2: Has file — run full pipeline ──────────────────────
            else:
                result = executor.execute(question=req.question, index_id=ws["index_id"])

            answer       = result.get("answer", "")
            query_type   = result.get("query_type", "rag")
            confidence   = result.get("confidence", None)
            intent       = result.get("intent", "answer")
            intent_label = result.get("intent_label", "🔍 RAG")
            viz_data     = result.get("viz_data", None)
            pdf_path     = result.get("pdf_path", None)

            # Store large data in cache — send only token through SSE
            import uuid as _uuid
            viz_token = None
            if viz_data:
                viz_token = str(_uuid.uuid4())
                _viz_cache[viz_token] = viz_data

            pdf_token = None
            if pdf_path:
                pdf_token = str(_uuid.uuid4())
                _pdf_cache[pdf_token] = pdf_path
                # Also store as latest pdf for this workspace (for report email)
                _workspace_pdf[workspace_id] = pdf_path
                # Store by BOTH workspace_id AND index_id so executor can find it
                # executor uses index_id as its key, main.py uses workspace_id
                index_id_for_cache = ws.get("index_id", workspace_id)
                executor.workspace_pdf_cache[workspace_id]        = pdf_path
                executor.workspace_pdf_cache[index_id_for_cache]  = pdf_path

            # Send metadata — no large payload
            meta = _json.dumps({
                "query_type":   query_type,
                "confidence":   confidence,
                "intent":       intent,
                "intent_label": intent_label,
                "viz_token":    viz_token,
                "pdf_token":    pdf_token,
                "workspace_id": workspace_id,
            })
            yield f"data: __META__{meta}\n\n"

            # ── Stream answer word by word ────────────────────────────────
            if not answer:
                yield "data: (No answer generated)\n\n"
            else:
                words = answer.split(" ")
                for i, word in enumerate(words):
                    token = word if i == len(words) - 1 else word + " "
                    # Escape newlines inside the SSE data field
                    token_escaped = token.replace("\n", "\\n")
                    yield f"data: {token_escaped}\n\n"
                    await asyncio.sleep(0.02)

            yield "data: __DONE__\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"data: __ERROR__Server error: {str(e)}\n\n"
            yield "data: __DONE__\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )

# ─────────────────────────────────────────────
# Visualization Data Endpoint
# ─────────────────────────────────────────────

@app.get("/workspace/{workspace_id}/latest_pdf", summary="Get latest PDF path for workspace")
def get_latest_pdf(workspace_id: str):
    path = _workspace_pdf.get(workspace_id)
    if not path:
        return {"pdf_path": None}
    return {"pdf_path": path}


@app.get("/pdf/{pdf_token}", summary="Download generated PDF report")
def download_pdf_report(pdf_token: str):
    """Serve generated PDF file by token."""
    import os
    from fastapi.responses import FileResponse
    path = _pdf_cache.get(pdf_token)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF not found or expired.")
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Analytics_Report.pdf"}
    )

@app.get("/viz/{viz_token}", summary="Fetch stored visualization data by token")
def get_viz_data(viz_token: str):
    """
    Frontend fetches full chart JSON using a token received in stream metadata.
    This avoids sending large JSON through SSE which can get truncated.
    """
    data = _viz_cache.get(viz_token)
    if not data:
        raise HTTPException(status_code=404, detail="Visualization data not found or expired.")
    return {"viz_data": data}

# ─────────────────────────────────────────────
# Quiz Endpoint
# ─────────────────────────────────────────────

quiz_generator = QuizGenerator(llm=llm, vector_store=vector_store, db=db)

class QuizRequest(BaseModel):
    difficulty: str = "medium"   # easy | medium | hard
    num_questions: int = 5       # 1–20

@app.post("/workspace/{workspace_id}/quiz", summary="Generate MCQ quiz from workspace file")
def generate_quiz(workspace_id: str, req: QuizRequest):
    """
    Generate a multiple choice quiz from the file uploaded in this workspace.
    - difficulty: easy / medium / hard
    - num_questions: 1 to 20
    Returns a list of questions with options A-D, correct answer, and explanation.
    """
    ws = workspaces.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    if not ws.get("index_id"):
        raise HTTPException(
            status_code=400,
            detail="This workspace has no file. Please upload a file before generating a quiz.",
        )

    if req.difficulty.lower() not in ["easy", "medium", "hard"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid difficulty. Choose 'easy', 'medium', or 'hard'.",
        )

    num = max(1, min(20, req.num_questions))

    logger.info(
        f"Quiz request | workspace_id={workspace_id} | "
        f"difficulty={req.difficulty} | num_questions={num}"
    )

    try:
        questions = quiz_generator.generate(
            index_id=ws["index_id"],
            difficulty=req.difficulty.lower(),
            num_questions=num,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate quiz. Please try again.")

    return {
        "workspace_id": workspace_id,
        "workspace_name": ws["name"],
        "difficulty": req.difficulty.lower(),
        "num_questions": len(questions),
        "questions": questions,
    }