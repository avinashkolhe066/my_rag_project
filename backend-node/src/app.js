const express = require("express");
const helmet = require("helmet");
const cors = require("cors");
require("express-async-errors");

const authRoutes = require("./routes/auth.routes");
const workspaceRoutes = require("./routes/workspace.routes");
const { errorHandler, notFound } = require("./middleware/error.middleware");

const app = express();

// ─────────────────────────────────────────────
// Security Middleware
// ─────────────────────────────────────────────

app.use(helmet());

app.use(
  cors({
    origin: process.env.ALLOWED_ORIGINS || "*",
    methods: ["GET", "POST", "PUT", "DELETE"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);

// ─────────────────────────────────────────────
// Body Parsers
// ─────────────────────────────────────────────

app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

// ─────────────────────────────────────────────
// Request Logger (simple, no external lib)
// ─────────────────────────────────────────────

app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// ─────────────────────────────────────────────
// Routes
// ─────────────────────────────────────────────

app.get("/", (req, res) => {
  res.json({
    status: "running",
    version: "1.0.0",
    service: "RAG Node.js API Gateway",
  });
});

app.use("/api/auth", authRoutes);
app.use("/api/workspaces", workspaceRoutes);

// ─────────────────────────────────────────────
// Error Handling (must be last)
// ─────────────────────────────────────────────

app.use(notFound);
app.use(errorHandler);

module.exports = app;
