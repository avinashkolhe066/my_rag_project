const express = require("express");
const multer = require("multer");
const Workspace = require("../models/Workspace");
const { protect } = require("../middleware/auth.middleware");
const ragService = require("../services/rag.service");

const router = express.Router();

// All workspace routes require authentication
router.use(protect);

// Multer: store file in memory so we can forward the buffer to Python
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB max
  fileFilter: (req, file, cb) => {
    const allowed = ["text/csv", "application/json", "application/pdf", "text/plain"];
    const allowedExt = [".csv", ".json", ".pdf", ".txt"];
    const ext = "." + file.originalname.split(".").pop().toLowerCase();

    if (allowed.includes(file.mimetype) || allowedExt.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error("Only CSV, JSON, PDF, and TXT files are allowed."));
    }
  },
});

// ─────────────────────────────────────────────
// Helper: verify workspace belongs to user
// ─────────────────────────────────────────────

const getOwnedWorkspace = async (workspaceId, userId) => {
  const workspace = await Workspace.findById(workspaceId);

  if (!workspace) {
    const err = new Error("Workspace not found.");
    err.statusCode = 404;
    throw err;
  }

  if (workspace.userId.toString() !== userId.toString()) {
    const err = new Error("Access denied. This workspace does not belong to you.");
    err.statusCode = 403;
    throw err;
  }

  return workspace;
};

// ─────────────────────────────────────────────
// POST /api/workspaces  — Create workspace
// ─────────────────────────────────────────────

router.post("/", async (req, res) => {
  const { name } = req.body;

  if (!name || !name.trim()) {
    return res.status(400).json({
      success: false,
      message: "Workspace name is required.",
    });
  }

  // Create workspace on Python RAG service first
  const pythonResponse = await ragService.createWorkspace(name.trim());

  // Save to MongoDB linked to this user
  const workspace = await Workspace.create({
    userId: req.user._id,
    name: name.trim(),
    pythonWorkspaceId: pythonResponse.workspace_id,
  });

  res.status(201).json({
    success: true,
    message: "Workspace created successfully.",
    workspace: {
      id: workspace._id,
      name: workspace.name,
      pythonWorkspaceId: workspace.pythonWorkspaceId,
      hasFile: workspace.hasFile,
      createdAt: workspace.createdAt,
    },
  });
});

// ─────────────────────────────────────────────
// GET /api/workspaces  — List user's workspaces
// ─────────────────────────────────────────────

router.get("/", async (req, res) => {
  const workspaces = await Workspace.find({ userId: req.user._id }).sort({
    createdAt: -1,
  });

  res.status(200).json({
    success: true,
    total: workspaces.length,
    workspaces: workspaces.map((ws) => ({
      id: ws._id,
      name: ws.name,
      pythonWorkspaceId: ws.pythonWorkspaceId,
      hasFile: ws.hasFile,
      fileName: ws.fileName,
      fileType: ws.fileType,
      createdAt: ws.createdAt,
    })),
  });
});

// ─────────────────────────────────────────────
// GET /api/workspaces/:id  — Get single workspace
// ─────────────────────────────────────────────

router.get("/:id", async (req, res) => {
  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);

  res.status(200).json({
    success: true,
    workspace: {
      id: workspace._id,
      name: workspace.name,
      pythonWorkspaceId: workspace.pythonWorkspaceId,
      hasFile: workspace.hasFile,
      fileName: workspace.fileName,
      fileType: workspace.fileType,
      createdAt: workspace.createdAt,
      updatedAt: workspace.updatedAt,
    },
  });
});

// ─────────────────────────────────────────────
// POST /api/workspaces/:id/ingest  — Upload file
// ─────────────────────────────────────────────

router.post("/:id/ingest", upload.single("file"), async (req, res) => {
  if (!req.file) {
    return res.status(400).json({
      success: false,
      message: "No file uploaded. Use form-data with key 'file'.",
    });
  }

  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);

  // Forward file buffer to Python RAG service
  const pythonResponse = await ragService.ingestFile(
    workspace.pythonWorkspaceId,
    req.file.buffer,
    req.file.originalname,
    req.file.mimetype
  );

  // Update workspace file info in MongoDB
  workspace.hasFile = true;
  workspace.fileName = req.file.originalname;
  workspace.fileType = pythonResponse.file_type || null;
  await workspace.save();

  res.status(200).json({
    success: true,
    message: "File uploaded and indexed successfully.",
    workspace: {
      id: workspace._id,
      name: workspace.name,
    },
    ingest: {
      fileName: req.file.originalname,
      fileType: pythonResponse.file_type,
      numChunks: pythonResponse.num_chunks,
      sqlTable: pythonResponse.sql_table || null,
    },
  });
});

// ─────────────────────────────────────────────
// POST /api/workspaces/:id/query  — Ask question
// ─────────────────────────────────────────────

router.post("/:id/query", async (req, res) => {
  const { question } = req.body;

  if (!question || !question.trim()) {
    return res.status(400).json({
      success: false,
      message: "Question is required.",
    });
  }

  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);

  if (!workspace.hasFile) {
    return res.status(400).json({
      success: false,
      message: "This workspace has no file. Please upload a file first.",
    });
  }

  // Forward question to Python RAG service
  const pythonResponse = await ragService.queryWorkspace(
    workspace.pythonWorkspaceId,
    question.trim()
  );

  res.status(200).json({
    success: true,
    workspace: {
      id: workspace._id,
      name: workspace.name,
    },
    result: pythonResponse,
  });
});

// ─────────────────────────────────────────────
// DELETE /api/workspaces/:id  — Delete workspace
// ─────────────────────────────────────────────

router.delete("/:id", async (req, res) => {
  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);

  // Delete from Python RAG service (removes FAISS index + history)
  await ragService.deleteWorkspace(workspace.pythonWorkspaceId);

  // Delete from MongoDB
  await Workspace.findByIdAndDelete(workspace._id);

  res.status(200).json({
    success: true,
    message: `Workspace '${workspace.name}' and all its data have been deleted.`,
  });
});

// ─────────────────────────────────────────────
// DELETE /api/workspaces/:id/history — Clear chat history
// ─────────────────────────────────────────────

router.delete("/:id/history", async (req, res) => {
  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);

  await ragService.clearHistory(workspace.pythonWorkspaceId);

  res.status(200).json({
    success: true,
    message: `Chat history cleared for workspace '${workspace.name}'.`,
  });
});

// ─────────────────────────────────────────────
// GET /api/workspaces/:id/history — Get chat history
// ─────────────────────────────────────────────

router.get("/:id/history", async (req, res) => {
  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);

  const history = await ragService.getHistory(workspace.pythonWorkspaceId);

  res.status(200).json({
    success: true,
    workspace: {
      id: workspace._id,
      name: workspace.name,
    },
    history,
  });
});

module.exports = router;
