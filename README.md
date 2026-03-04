# 🧠 RAG Platform — AI Document Intelligence

> A full-stack, production-ready AI platform that lets users upload documents, chat with them using natural language or SQL, and generate MCQ quizzes — all powered by a local LLM (Ollama) or Google Gemini.

---

## 📸 Overview

RAG Platform is a **microservice-based** AI application with three independently running services:

| Service | Tech | Port |
|---------|------|------|
| 🐍 Python RAG Engine | FastAPI + FAISS + Ollama | `8000` |
| 🟢 Node.js API Gateway | Express + MongoDB + JWT | `5000` |
| ⚛️ React Frontend | Vite + Tailwind CSS | `5173` |

---

## ✨ Features

### 🗂️ Workspace System
- Create isolated workspaces — each with its own file, RAG index, and chat history
- Upload CSV, JSON, PDF, or TXT files per workspace
- Delete workspaces with full data cleanup (FAISS index + chat history)

### 💬 Hybrid RAG Chat
- **PDF / TXT** → always uses semantic search (FAISS + embeddings)
- **CSV / JSON** → auto-detects raw SQL vs natural language
  - Raw `SELECT` queries → execute directly on SQLite
  - Natural language → LLM decides SQL or RAG
- Conversation memory — follow-up questions like *"tell me more"* work
- Query type badge on every response (`RAG`, `SQL`, `SQL Aggregate`, `Error`)

### 🧩 MCQ Quiz Generator
- Select workspace, difficulty (Easy / Medium / Hard), and number of questions (1–20)
- LLM reads document chunks and generates multiple choice questions
- Per-question countdown timer
- Instant feedback + explanation after each answer
- Final results screen with score, donut chart, correct/wrong/skipped breakdown
- Full review mode — go through every question with correct answer highlighted

### 🔐 Authentication & Security
- JWT-based authentication (7-day expiry)
- bcrypt password hashing
- Internal API key between Node and Python (never exposed to client)
- Protected routes — all workspace and quiz endpoints require valid JWT
- Workspace ownership enforcement — users can only access their own workspaces

### 🎨 UI/UX
- Dark mode (deep navy, like a fintech dashboard) / Light mode (warm beige + black)
- Collapsible sidebar
- Framer Motion animations — page transitions, staggered cards, chat bubbles
- Drag & drop file upload
- Fully responsive

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│              Vite + Tailwind + Framer Motion             │
│                   localhost:5173                         │
└─────────────────────┬───────────────────────────────────┘
                      │  HTTP (JWT in Authorization header)
                      ▼
┌─────────────────────────────────────────────────────────┐
│               Node.js API Gateway                        │
│            Express + MongoDB + bcrypt + JWT              │
│                   localhost:5000                         │
│                                                          │
│  • Handles auth (register / login)                       │
│  • Stores users + workspace metadata in MongoDB          │
│  • Verifies ownership before proxying requests           │
│  • Forwards requests to Python with X-Internal-API-Key   │
└─────────────────────┬───────────────────────────────────┘
                      │  HTTP + X-Internal-API-Key header
                      ▼
┌─────────────────────────────────────────────────────────┐
│              Python RAG Engine                           │
│         FastAPI + FAISS + SentenceTransformers           │
│                   localhost:8000                         │
│                                                          │
│  • Parses uploaded files (CSV / JSON / PDF / TXT)        │
│  • Builds FAISS vector index per workspace               │
│  • Runs hybrid SQL + semantic search queries             │
│  • Generates MCQ quizzes via LLM                         │
│  • Maintains conversation memory per workspace           │
└─────────────────────┬───────────────────────────────────┘
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   ┌─────────────┐        ┌──────────────┐
   │   Ollama    │        │    Gemini    │
   │ (local LLM) │   OR   │  (Google AI) │
   │ qwen2.5:7b  │        │   API key    │
   └─────────────┘        └──────────────┘
```

---

## 📁 Project Structure

```
rag-platform/
│
├── my_rag_project/                  ← Python RAG Engine
│   ├── main.py                      ← FastAPI app + all endpoints
│   ├── config.py                    ← Settings loaded from .env
│   ├── llm_client.py                ← Ollama + Gemini wrapper
│   ├── database.py                  ← SQLite operations
│   ├── memory.py                    ← Conversation history per workspace
│   ├── workspace.py                 ← Workspace manager (persisted to JSON)
│   ├── quiz_generator.py            ← MCQ quiz generation via LLM
│   ├── internal_auth.py             ← X-Internal-API-Key middleware
│   ├── ingestion/
│   │   ├── file_handler.py          ← Parse CSV, JSON, PDF, TXT
│   │   └── vector_store.py          ← FAISS save, search, delete
│   ├── query/
│   │   ├── planner.py               ← LLM decides SQL vs RAG
│   │   └── executor.py              ← Runs query strategy + memory
│   ├── utils/
│   │   └── logger.py                ← Rotating file + console logger
│   ├── .env                         ← Python config
│   └── requirements.txt
│
├── backend-node/                    ← Node.js API Gateway
│   ├── server.js                    ← Entry point
│   ├── src/
│   │   ├── app.js                   ← Express setup + middleware
│   │   ├── config/db.js             ← MongoDB connection
│   │   ├── models/
│   │   │   ├── User.js              ← User schema
│   │   │   └── Workspace.js         ← Workspace schema
│   │   ├── middleware/
│   │   │   ├── auth.middleware.js   ← JWT verification
│   │   │   └── error.middleware.js  ← Global error handler
│   │   ├── services/
│   │   │   └── rag.service.js       ← All axios calls to Python
│   │   └── routes/
│   │       ├── auth.routes.js       ← /api/auth/*
│   │       └── workspace.routes.js  ← /api/workspaces/*
│   ├── .env
│   └── package.json
│
└── rag-frontend/                    ← React Frontend
    ├── src/
    │   ├── api/
    │   │   ├── axios.js             ← Axios instance + interceptors
    │   │   ├── auth.service.js      ← Auth API calls
    │   │   └── workspace.service.js ← Workspace + quiz API calls
    │   ├── context/
    │   │   ├── AuthContext.jsx      ← User state + login/logout
    │   │   └── ThemeContext.jsx     ← Dark/light mode
    │   ├── components/
    │   │   ├── Navbar.jsx
    │   │   ├── Sidebar.jsx
    │   │   ├── ThemeToggle.jsx
    │   │   ├── StatCard.jsx
    │   │   ├── WorkspaceCard.jsx
    │   │   ├── CreateWorkspaceModal.jsx
    │   │   ├── FileUpload.jsx
    │   │   ├── ChatWindow.jsx
    │   │   ├── MessageBubble.jsx
    │   │   ├── ProtectedRoute.jsx
    │   │   └── LoadingSpinner.jsx
    │   ├── pages/
    │   │   ├── Login.jsx
    │   │   ├── Register.jsx
    │   │   ├── Dashboard.jsx
    │   │   ├── WorkspacePage.jsx
    │   │   └── QuizPage.jsx
    │   ├── App.jsx
    │   ├── main.jsx
    │   └── index.css                ← CSS variables for both themes
    ├── tailwind.config.js
    └── package.json
```

---

## ⚙️ Prerequisites

Make sure you have all of these installed before starting:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.10+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| MongoDB | 6+ | https://mongodb.com/try/download/community |
| Ollama | Latest | https://ollama.com/download |
| Git | Any | https://git-scm.com |

---

## 🚀 Installation & Setup

### Step 1 — Clone the repository

```bash
git clone https://github.com/yourusername/rag-platform.git
cd rag-platform
```

---

### Step 2 — Setup Python RAG Engine

```bash
cd my_rag_project

# Create virtual environment
python -m venv venv

# Activate (Windows CMD)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create `.env` file in `my_rag_project/`:

```env
LLM_BACKEND=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=300
CHUNK_OVERLAP=50
TOP_K_RESULTS=10
API_HOST=0.0.0.0
API_PORT=8000
INTERNAL_SECRET=your_internal_secret_here
```

Pull the LLM model:

```bash
ollama pull qwen2.5:7b
```

---

### Step 3 — Setup Node.js API Gateway

```bash
cd ../backend-node
npm install
```

Create `.env` file in `backend-node/`:

```env
PORT=5000
MONGO_URI=mongodb://localhost:27017/rag_platform
JWT_SECRET=your_long_random_jwt_secret_here
INTERNAL_SECRET=your_internal_secret_here
PYTHON_API=http://localhost:8000
```

> ⚠️ `INTERNAL_SECRET` must be **identical** in both `.env` files.

Generate secure secrets using Node.js:

```bash
node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
```

Run this twice — use one value for `JWT_SECRET` and another for `INTERNAL_SECRET`.

---

### Step 4 — Setup React Frontend

```bash
cd ../rag-frontend
npm install
```

No `.env` needed — the API base URL (`http://localhost:5000`) is set in `src/api/axios.js`.

---

## ▶️ Running the Application

Open **4 terminal windows** and run each command:

```bash
# Terminal 1 — Ollama LLM server
ollama serve

# Terminal 2 — MongoDB (if not running as service)
mongod

# Terminal 3 — Python RAG Engine
cd my_rag_project
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
uvicorn main:app --reload --port 8000

# Terminal 4 — Node.js API Gateway
cd backend-node
npm run dev

# Terminal 5 — React Frontend
cd rag-frontend
npm run dev
```

Then open your browser at:

```
http://localhost:5173
```

---

## 📡 API Reference

### Auth Endpoints (Node.js — port 5000)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/auth/register` | `{ name, email, password }` | Create account, returns JWT |
| `POST` | `/api/auth/login` | `{ email, password }` | Login, returns JWT |
| `GET`  | `/api/auth/me` | — | Get current user info |

### Workspace Endpoints (Node.js — port 5000)

All workspace routes require: `Authorization: Bearer <token>`

| Method | Endpoint | Body / Form | Description |
|--------|----------|-------------|-------------|
| `POST` | `/api/workspaces` | `{ name }` | Create workspace |
| `GET`  | `/api/workspaces` | — | List user's workspaces |
| `GET`  | `/api/workspaces/:id` | — | Get workspace details |
| `POST` | `/api/workspaces/:id/ingest` | `form-data: file` | Upload file to workspace |
| `POST` | `/api/workspaces/:id/query` | `{ question }` | Ask a question |
| `POST` | `/api/workspaces/:id/quiz` | `{ difficulty, num_questions }` | Generate MCQ quiz |
| `DELETE` | `/api/workspaces/:id` | — | Delete workspace + data |
| `DELETE` | `/api/workspaces/:id/history` | — | Clear chat history |
| `GET`  | `/api/workspaces/:id/history` | — | Get chat history |

### Python Direct Endpoints (port 8000)

> 🔒 Requires `X-Internal-API-Key` header. Do not call directly from frontend.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Health check |
| `POST` | `/workspace` | Create workspace |
| `GET`  | `/workspace` | List workspaces |
| `GET`  | `/workspace/:id` | Get workspace |
| `POST` | `/workspace/:id/ingest` | Upload file |
| `POST` | `/workspace/:id/query` | Query document |
| `POST` | `/workspace/:id/quiz` | Generate quiz |
| `DELETE` | `/workspace/:id` | Delete workspace |

---

## 🔄 Complete User Flow

```
1. Register / Login
        ↓
2. Dashboard — create a workspace (e.g. "Study Notes")
        ↓
3. Open workspace → upload a PDF/CSV/TXT file
        ↓
4. Chat with your document
   - "Summarize this document"
   - "What are the key concepts?"
   - "SELECT * FROM data WHERE column > 100"  ← raw SQL for CSV
        ↓
5. Go to Quiz page
   - Select workspace
   - Choose difficulty: Easy / Medium / Hard
   - Choose number of questions: 5 / 10 / 15 / 20
   - Solve MCQ quiz with countdown timer
   - See your score and review all answers
```

---

## 🧠 Query Routing Logic

```
Uploaded file type?
│
├── PDF / TXT
│     └── Always → FAISS semantic search → LLM answer
│
└── CSV / JSON
      ├── Question starts with SELECT?
      │     └── Raw SQL → Execute on SQLite → Return rows
      │
      └── Natural language?
            └── LLM reads schema → decides:
                  ├── SQL path → Generate SQL → Execute → LLM formats answer
                  └── RAG path → FAISS search → LLM answer
```

---

## 🎯 Quiz Generation Logic

```
User selects: workspace + difficulty + num_questions
        ↓
Python fetches broad document chunks from FAISS
(3 generic queries to get diverse content)
        ↓
LLM receives chunks + difficulty instructions + count
        ↓
LLM returns JSON array of questions:
{
  "question": "...",
  "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
  "correct": "B",
  "explanation": "..."
}
        ↓
Validated + cleaned → sent to frontend
        ↓
Quiz starts with per-question timer:
  Easy → 30s | Medium → 45s | Hard → 60s
```

---

## 🎨 Theme System

The UI uses CSS custom properties for theming — defined once in `index.css`, used everywhere.

| Variable | Light Mode | Dark Mode |
|----------|------------|-----------|
| `--page-bg` | `#faf8f4` (warm cream) | `#0d1021` (deep navy) |
| `--card-bg` | `#ffffff` | `#181c2e` |
| `--text-1` | `#1a1208` (rich black) | `#e8ecff` (soft white) |
| `--accent` | `#4f46e5` (indigo) | `#818cf8` (light indigo) |
| `--green` | `#16a34a` | `#4ade80` |

---

## 🔒 Security Notes

- Passwords are hashed with **bcrypt** (10 salt rounds) — never stored in plain text
- JWT tokens expire in **7 days**
- The Python RAG engine is protected by `X-Internal-API-Key` — it should never be exposed to the public internet
- Users can only access their own workspaces — ownership is verified on every request
- CORS and Helmet are configured on the Node.js server
- File uploads are limited to **50MB** and restricted to CSV, JSON, PDF, TXT only

---

## 🛠️ Tech Stack Summary

### Python RAG Engine
| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `faiss-cpu` | Vector similarity search |
| `sentence-transformers` | Text embeddings (all-MiniLM-L6-v2) |
| `pandas` | CSV/JSON tabular data processing |
| `PyPDF2` | PDF text extraction |
| `python-dotenv` | Environment variable loading |

### Node.js API Gateway
| Package | Purpose |
|---------|---------|
| `express` | Web framework |
| `mongoose` | MongoDB ODM |
| `bcryptjs` | Password hashing |
| `jsonwebtoken` | JWT creation and verification |
| `axios` | HTTP client for Python proxy |
| `multer` | File upload handling |
| `helmet` | HTTP security headers |
| `cors` | Cross-Origin Resource Sharing |

### React Frontend
| Package | Purpose |
|---------|---------|
| `react` + `vite` | UI framework + build tool |
| `react-router-dom` | Client-side routing |
| `framer-motion` | Animations and transitions |
| `react-hot-toast` | Toast notifications |
| `lucide-react` | Icon library |
| `axios` | HTTP client |
| `tailwindcss` | Utility-first CSS |

---

## 🐛 Troubleshooting

### Python server won't start
```bash
# Make sure virtual environment is activated
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac/Linux

# Reinstall dependencies
pip install -r requirements.txt --break-system-packages
```

### Ollama connection refused
```bash
# Make sure Ollama is running
ollama serve

# Check model is downloaded
ollama list

# Re-pull model if missing
ollama pull qwen2.5:7b
```

### MongoDB connection failed
```bash
# Start MongoDB service
mongod

# Or on Windows as a service
net start MongoDB
```

### Node.js 401 errors
- Check that `JWT_SECRET` is set in `backend-node/.env`
- Make sure the token is being sent as `Authorization: Bearer <token>`
- Token may have expired — log out and log back in

### Quiz generation timeout
- Quiz generation can take 30–90 seconds depending on the LLM
- If it consistently fails, try reducing `num_questions`
- Make sure the file is properly uploaded before generating quiz

### 403 Forbidden from Python
- `INTERNAL_SECRET` in `backend-node/.env` and `my_rag_project/.env` must be **identical**

---

## 📝 Environment Variables Reference

### `my_rag_project/.env`

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_BACKEND` | ✅ | `ollama` | `ollama` or `gemini` |
| `OLLAMA_URL` | ✅ | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | ✅ | `qwen2.5:7b` | Model name |
| `GEMINI_API_KEY` | ⚠️ | — | Required if using Gemini |
| `INTERNAL_SECRET` | ✅ | — | Must match Node.js value |
| `CHUNK_SIZE` | ❌ | `300` | Text chunk size for embeddings |
| `TOP_K_RESULTS` | ❌ | `10` | Number of chunks to retrieve |

### `backend-node/.env`

| Variable | Required | Description |
|----------|----------|-------------|
| `PORT` | ✅ | Node.js server port (default `5000`) |
| `MONGO_URI` | ✅ | MongoDB connection string |
| `JWT_SECRET` | ✅ | Long random string for JWT signing |
| `INTERNAL_SECRET` | ✅ | Must match Python value |
| `PYTHON_API` | ✅ | Python server URL (default `http://localhost:8000`) |

---

## 🚧 Known Limitations

- Scanned PDFs (image-based) are not supported — only text-based PDFs work
- Conversation memory is lost when the Python server restarts (in-memory only)
- One file per workspace — uploading a new file replaces the old one
- No real-time streaming of LLM responses (full response arrives at once)
- Quiz generation requires the LLM to be responsive — very large documents may hit token limits

---

## 🗺️ Roadmap

- [ ] Streaming LLM responses (Server-Sent Events)
- [ ] Multi-file workspaces
- [ ] Persistent conversation history (SQLite/MongoDB)
- [ ] OCR support for scanned PDFs
- [ ] Quiz history and leaderboard
- [ ] Export chat as PDF
- [ ] Share workspace with other users
- [ ] Docker Compose setup for one-command deployment

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👨‍💻 Author

Built with ❤️ using FastAPI, Express, React, and Ollama.

---

> **RAG Platform** — Upload. Chat. Learn. All in one place.
