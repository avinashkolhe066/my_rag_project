const express = require("express");
const multer = require("multer");
const Workspace = require("../models/Workspace");
const { protect } = require("../middleware/auth.middleware");
const ragService   = require("../services/rag.service");
const emailService = require("../services/email.service");

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

// GET /api/workspaces/pdf/:token — Download generated PDF report
router.get("/pdf/:token", async (req, res) => {
  // Allow auth via query param ?auth=<jwt> for browser direct downloads
  const token = req.headers.authorization?.replace("Bearer ", "").trim()
             || req.query.auth;

  if (!token) {
    return res.status(401).json({ error: "Not authenticated." });
  }

  // Verify JWT
  try {
    const jwt = require("jsonwebtoken");
    jwt.verify(token, process.env.JWT_SECRET);
  } catch (e) {
    return res.status(401).json({ error: "Invalid token." });
  }

  try {
    const axios = require("axios");
    const upstream = await axios.get(
      `${process.env.PYTHON_API}/pdf/${req.params.token}`,
      {
        headers: { "x-internal-secret": process.env.INTERNAL_SECRET },
        responseType: "stream",
      }
    );
    res.setHeader("Content-Type", "application/pdf");
    res.setHeader("Content-Disposition", "attachment; filename=Analytics_Report.pdf");
    upstream.data.pipe(res);
  } catch (e) {
    res.status(404).json({ error: "PDF not found." });
  }
});

// GET /api/workspaces/viz/:token — Fetch visualization data by token
router.get("/viz/:token", async (req, res) => {
  try {
    const axios = require("axios");
    const result = await axios.get(
      `${process.env.PYTHON_API}/viz/${req.params.token}`,
      { headers: { "x-internal-secret": process.env.INTERNAL_SECRET } }
    );
    res.json(result.data);
  } catch (e) {
    res.status(404).json({ error: "Visualization data not found." });
  }
});

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
    return res.status(400).json({ success: false, message: "Question is required." });
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

  // ── Handle email sending via Nodemailer ──────────────────────────────
  console.log("[EMAIL] query_type:", pythonResponse.query_type);
  console.log("[EMAIL] email_mode:", pythonResponse.email_mode);
  console.log("[EMAIL] recipients count:", pythonResponse.recipients?.length ?? 0);

  if (
    pythonResponse.query_type === "send_email" &&
    pythonResponse.email_mode &&
    pythonResponse.recipients?.length > 0
  ) {
    console.log("[EMAIL] Entering send block — mode:", pythonResponse.email_mode);
    const { email_mode, recipients, ...cleanResult } = pythonResponse;

    try {
      let answerText;

      if (email_mode === "bulk") {
        console.log("[EMAIL] Sending bulk to", recipients.length, "recipients");
        const emailResult = await emailService.sendBulkEmails(recipients);
        console.log("[EMAIL] Bulk result:", emailResult);
        answerText =
          `EMAIL_SENT_BULK::${emailResult.sent}::${emailResult.failed}::` +
          (emailResult.errors.length ? emailResult.errors.join("; ") : "");
      } else {
        const recip = recipients[0];
        console.log("[EMAIL] Sending single to:", recip.to, "| subject:", recip.subject);
        await emailService.sendSingleEmail(recip);
        console.log("[EMAIL] Single send SUCCESS to:", recip.to);
        answerText = `EMAIL_SENT_SINGLE::${recip.to}::${recip.subject}`;
      }

      cleanResult.answer = answerText;
      return res.status(200).json({
        success: true,
        workspace: { id: workspace._id, name: workspace.name },
        result: cleanResult,
      });

    } catch (err) {
      console.error("[EMAIL] Send FAILED:", err.message);
      cleanResult.answer = `❌ Email failed: ${err.message}`;
      return res.status(200).json({
        success: true,
        workspace: { id: workspace._id, name: workspace.name },
        result: cleanResult,
      });
    }
  } else if (pythonResponse.query_type === "send_email") {
    // Python returned send_email but without email_mode — means error/invalid address
    console.log("[EMAIL] Python returned send_email with no payload — showing Python answer as-is");
  }

  // Default — return Python response as-is
  res.status(200).json({
    success: true,
    workspace: { id: workspace._id, name: workspace.name },
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

  try {
    // Timeout after 3s — never block the UI waiting for history
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error("History timeout")), 3000)
    );
    const result = await Promise.race([
      ragService.getHistory(workspace.pythonWorkspaceId),
      timeoutPromise,
    ]);
    const history = Array.isArray(result?.history) ? result.history : [];
    res.status(200).json({ success: true, history });
  } catch (err) {
    // On timeout or error — return empty history so UI never hangs
    console.warn("[History] Returning empty — reason:", err.message);
    res.status(200).json({ success: true, history: [] });
  }
});


// ─────────────────────────────────────────────

// POST /api/workspaces/:id/stream — Streaming SSE query
// ─────────────────────────────────────────────

router.post("/:id/stream", async (req, res) => {
  const { question } = req.body;
  if (!question?.trim()) {
    return res.status(400).json({ success: false, message: "Question is required." });
  }

  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);
  const axios = require("axios");

  // ── Email intent: use regular query endpoint, not stream ─────────────
  // Stream just pipes bytes — we can't intercept it for email sending.
  // So for send_email intent we call /query directly, handle Nodemailer,
  // then emit the result as a single SSE event so the frontend still works.
  try {
    const pythonQueryResponse = await axios({
      method: "POST",
      url: `${process.env.PYTHON_API}/workspace/${workspace.pythonWorkspaceId}/query`,
      data: { question },
      headers: {
        "Content-Type": "application/json",
        "X-Internal-API-Key": process.env.INTERNAL_SECRET,
      },
      timeout: 120000,
    });

    const pythonResponse = pythonQueryResponse.data;

    const isEmailIntent = ["send_email", "send_report_email"].includes(pythonResponse.query_type);

    // Only log when it's actually an email request
    if (isEmailIntent) {
      console.log("[EMAIL] query_type:", pythonResponse.query_type);
      console.log("[EMAIL] email_mode:", pythonResponse.email_mode);
      console.log("[EMAIL] recipients:", pythonResponse.recipients?.length ?? 0);
    }

    if (
      isEmailIntent &&
      pythonResponse.email_mode &&
      pythonResponse.recipients?.length > 0
    ) {
      console.log("[STREAM/EMAIL] Handling email — mode:", pythonResponse.email_mode, "type:", pythonResponse.query_type);
      const { email_mode, recipients, pdf_path, ...cleanResult } = pythonResponse;

      // ── If report email, fetch the PDF from Python and attach it ────────
      let pdfBuffer = null;
      let pdfFilename = null;
      if (pythonResponse.query_type === "send_report_email") {
        try {
          // Try pdf_path from payload first, else fetch latest from Python
          let resolvedPath = pdf_path;
          if (!resolvedPath) {
            const latestRes = await axios.get(
              `${process.env.PYTHON_API}/workspace/${workspace.pythonWorkspaceId}/latest_pdf`,
              { headers: { "X-Internal-API-Key": process.env.INTERNAL_SECRET } }
            );
            resolvedPath = latestRes.data?.pdf_path;
          }
          if (resolvedPath) {
            const fs = require("fs");
            if (fs.existsSync(resolvedPath)) {
              pdfBuffer   = fs.readFileSync(resolvedPath);
              pdfFilename = require("path").basename(resolvedPath);
              console.log("[STREAM/EMAIL] PDF attached:", pdfFilename, "size:", pdfBuffer.length);
            } else {
              console.warn("[STREAM/EMAIL] PDF path not found on disk:", resolvedPath);
            }
          } else {
            console.warn("[STREAM/EMAIL] No PDF found for this workspace");
          }
        } catch (pdfErr) {
          console.warn("[STREAM/EMAIL] Could not fetch PDF:", pdfErr.message);
        }
      }

      try {
        let answerText;
        if (email_mode === "bulk") {
          const emailResult = await emailService.sendBulkEmails(recipients, pdfBuffer, pdfFilename);
          console.log("[STREAM/EMAIL] Bulk result:", emailResult);
          answerText =
            `EMAIL_SENT_BULK::${emailResult.sent}::${emailResult.failed}::` +
            (emailResult.errors.length ? emailResult.errors.join("; ") : "");
        } else {
          const recip = recipients[0];
          console.log("[STREAM/EMAIL] Sending to:", recip.to);
          await emailService.sendSingleEmail(recip, pdfBuffer, pdfFilename);
          console.log("[STREAM/EMAIL] ✓ Sent to:", recip.to);
          answerText = `EMAIL_SENT_SINGLE::${recip.to}::${recip.subject}`;
        }
        cleanResult.answer = answerText;

        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");
        res.flushHeaders();
        res.write(`data: ${cleanResult.answer}\n\n`);
        res.write(`data: __META__${JSON.stringify(cleanResult)}\n\n`);
        res.write("data: __DONE__\n\n");
        return res.end();

      } catch (err) {
        console.error("[STREAM/EMAIL] Send FAILED:", err.message);
        cleanResult.answer = `❌ Email failed: ${err.message}`;
        res.setHeader("Content-Type", "text/event-stream");
        res.setHeader("Cache-Control", "no-cache");
        res.setHeader("Connection", "keep-alive");
        res.flushHeaders();
        res.write(`data: ${cleanResult.answer}\n\n`);
        res.write(`data: __META__${JSON.stringify(cleanResult)}\n\n`);
        res.write("data: __DONE__\n\n");
        return res.end();
      }
    }

    // ── Not an email — fall through to normal SSE stream ─────────────────
  } catch (preCheckErr) {
    console.warn("[STREAM] Pre-check query failed, falling through to stream:", preCheckErr.message);
  }

  // Set SSE headers for normal streaming
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("X-Accel-Buffering", "no");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.flushHeaders();

  try {
    const upstream = await axios({
      method: "POST",
      url: `${process.env.PYTHON_API}/workspace/${workspace.pythonWorkspaceId}/stream`,
      data: { question },
      headers: {
        "Content-Type": "application/json",
        "X-Internal-API-Key": process.env.INTERNAL_SECRET,
      },
      responseType: "stream",
      timeout: 120000,
    });

    upstream.data.pipe(res);

    req.on("close", () => {
      upstream.data.destroy();
    });

    upstream.data.on("error", (err) => {
      res.write(`data: __ERROR__${err.message}\n\n`);
      res.end();
    });

  } catch (err) {
    const msg = err.response?.data || err.message || "Stream failed";
    res.write(`data: __ERROR__${msg}\n\n`);
    res.end();
  }
});

module.exports = router;

// ─────────────────────────────────────────────
// POST /api/workspaces/:id/quiz — Generate MCQ quiz
// ─────────────────────────────────────────────

router.post("/:id/quiz", async (req, res) => {
  const { difficulty = "medium", num_questions = 5 } = req.body;

  const VALID_DIFFICULTIES = ["easy", "medium", "hard"];
  if (!VALID_DIFFICULTIES.includes(difficulty.toLowerCase())) {
    return res.status(400).json({
      success: false,
      message: "Invalid difficulty. Choose 'easy', 'medium', or 'hard'.",
    });
  }

  const numQ = Math.max(1, Math.min(20, parseInt(num_questions) || 5));

  const workspace = await getOwnedWorkspace(req.params.id, req.user._id);

  if (!workspace.hasFile) {
    return res.status(400).json({
      success: false,
      message: "This workspace has no file. Please upload a file before generating a quiz.",
    });
  }

  const quizData = await ragService.generateQuiz(
    workspace.pythonWorkspaceId,
    difficulty.toLowerCase(),
    numQ
  );

  res.status(200).json({
    success: true,
    workspace: { id: workspace._id, name: workspace.name },
    quiz: quizData,
  });
});