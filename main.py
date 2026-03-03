import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import config
from llm_client import LLMClient
from database import DatabaseManager
from memory import ConversationMemory
from workspace import WorkspaceManager
from ingestion.file_handler import parse_file
from ingestion.vector_store import VectorStore
from query.executor import QueryExecutor
from utils.logger import get_logger
from internal_auth import InternalAPIKeyMiddleware

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
executor     = QueryExecutor(llm=llm, db=db, vector_store=vector_store)

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

    if not ws.get("index_id"):
        raise HTTPException(
            status_code=400,
            detail="This workspace has no file. Please upload a file first.",
        )

    logger.info(
        f"Query | workspace_id={workspace_id} | "
        f"file={ws['file_name']} | question={req.question[:80]}"
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
