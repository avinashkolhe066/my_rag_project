const axios = require("axios");
const FormData = require("form-data");

const ragClient = axios.create({
  baseURL: process.env.PYTHON_API,
  timeout: 120000,
  headers: { "X-Internal-API-Key": process.env.INTERNAL_SECRET },
});

const createWorkspace = async (name) => {
  const { data } = await ragClient.post("/workspace", { name });
  return data;
};

const listWorkspaces = async () => {
  const { data } = await ragClient.get("/workspace");
  return data;
};

const getWorkspace = async (pythonWorkspaceId) => {
  const { data } = await ragClient.get(`/workspace/${pythonWorkspaceId}`);
  return data;
};

const deleteWorkspace = async (pythonWorkspaceId) => {
  const { data } = await ragClient.delete(`/workspace/${pythonWorkspaceId}`);
  return data;
};

const ingestFile = async (pythonWorkspaceId, fileBuffer, originalName, mimetype) => {
  const form = new FormData();
  form.append("file", fileBuffer, { filename: originalName, contentType: mimetype });
  const { data } = await ragClient.post(
    `/workspace/${pythonWorkspaceId}/ingest`, form,
    { headers: { ...form.getHeaders(), "X-Internal-API-Key": process.env.INTERNAL_SECRET }, timeout: 180000 }
  );
  return data;
};

const queryWorkspace = async (pythonWorkspaceId, question) => {
  const { data } = await ragClient.post(`/workspace/${pythonWorkspaceId}/query`, { question });
  return data;
};

const clearHistory = async (pythonWorkspaceId) => {
  const { data } = await ragClient.delete(`/workspace/${pythonWorkspaceId}/history`);
  return data;
};

const getHistory = async (pythonWorkspaceId) => {
  const { data } = await ragClient.get(`/history/${pythonWorkspaceId}`);
  return data;
};

const generateQuiz = async (pythonWorkspaceId, difficulty, numQuestions) => {
  const { data } = await ragClient.post(
    `/workspace/${pythonWorkspaceId}/quiz`,
    { difficulty, num_questions: numQuestions },
    { timeout: 180000 }
  );
  return data;
};

module.exports = {
  createWorkspace, listWorkspaces, getWorkspace, deleteWorkspace,
  ingestFile, queryWorkspace, clearHistory, getHistory, generateQuiz,
};
