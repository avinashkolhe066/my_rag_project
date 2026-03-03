const axios = require("axios");
const FormData = require("form-data");

/**
 * Axios instance pre-configured with:
 *   - Python base URL from env
 *   - Internal API key header on every request
 *   - 60s timeout
 */
const ragClient = axios.create({
  baseURL: process.env.PYTHON_API,
  timeout: 120000, // 120s — LLM responses can be slow
  headers: {
    "X-Internal-API-Key": process.env.INTERNAL_SECRET,
  },
});

// ─────────────────────────────────────────────
// Workspace operations
// ─────────────────────────────────────────────

/**
 * Create a new workspace on the Python RAG service.
 * @param {string} name - Workspace name
 * @returns {object} Python workspace response { workspace_id, name, ... }
 */
const createWorkspace = async (name) => {
  const { data } = await ragClient.post("/workspace", { name });
  return data;
};

/**
 * Get all workspaces from Python (used for health checks if needed).
 */
const listWorkspaces = async () => {
  const { data } = await ragClient.get("/workspace");
  return data;
};

/**
 * Get details of a specific Python workspace.
 * @param {string} pythonWorkspaceId
 */
const getWorkspace = async (pythonWorkspaceId) => {
  const { data } = await ragClient.get(`/workspace/${pythonWorkspaceId}`);
  return data;
};

/**
 * Delete a workspace on the Python RAG service.
 * @param {string} pythonWorkspaceId
 */
const deleteWorkspace = async (pythonWorkspaceId) => {
  const { data } = await ragClient.delete(`/workspace/${pythonWorkspaceId}`);
  return data;
};

// ─────────────────────────────────────────────
// File ingestion
// ─────────────────────────────────────────────

/**
 * Forward a file upload to the Python RAG service.
 * @param {string} pythonWorkspaceId
 * @param {Buffer} fileBuffer - raw file bytes
 * @param {string} originalName - original filename (used to detect file type)
 * @param {string} mimetype - MIME type of the file
 * @returns {object} Python ingest response
 */
const ingestFile = async (pythonWorkspaceId, fileBuffer, originalName, mimetype) => {
  const form = new FormData();
  form.append("file", fileBuffer, {
    filename: originalName,
    contentType: mimetype,
  });

  const { data } = await ragClient.post(
    `/workspace/${pythonWorkspaceId}/ingest`,
    form,
    {
      headers: {
        ...form.getHeaders(),
        "X-Internal-API-Key": process.env.INTERNAL_SECRET,
      },
      // Override timeout for large files
      timeout: 180000,
    }
  );

  return data;
};

// ─────────────────────────────────────────────
// Query
// ─────────────────────────────────────────────

/**
 * Forward a natural language question or raw SQL to the Python RAG service.
 * @param {string} pythonWorkspaceId
 * @param {string} question
 * @returns {object} Python query response { answer, query_type, ... }
 */
const queryWorkspace = async (pythonWorkspaceId, question) => {
  const { data } = await ragClient.post(`/workspace/${pythonWorkspaceId}/query`, {
    question,
  });
  return data;
};

/**
 * Clear conversation history for a workspace.
 * @param {string} pythonWorkspaceId
 */
const clearHistory = async (pythonWorkspaceId) => {
  const { data } = await ragClient.delete(
    `/workspace/${pythonWorkspaceId}/history`
  );
  return data;
};

/**
 * Get conversation history for a workspace.
 * @param {string} pythonWorkspaceId
 */
const getHistory = async (pythonWorkspaceId) => {
  const { data } = await ragClient.get(`/history/${pythonWorkspaceId}`);
  return data;
};

module.exports = {
  createWorkspace,
  listWorkspaces,
  getWorkspace,
  deleteWorkspace,
  ingestFile,
  queryWorkspace,
  clearHistory,
  getHistory,
};
