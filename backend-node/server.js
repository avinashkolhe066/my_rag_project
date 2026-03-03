require("dotenv").config();
const app = require("./src/app");
const connectDB = require("./src/config/db");

const PORT = process.env.PORT || 5000;

const start = async () => {
  try {
    await connectDB();
    app.listen(PORT, () => {
      console.log("─────────────────────────────────────");
      console.log(`  RAG Node.js API Gateway`);
      console.log(`  Running on: http://localhost:${PORT}`);
      console.log(`  MongoDB: connected`);
      console.log(`  Python RAG: ${process.env.PYTHON_API}`);
      console.log("─────────────────────────────────────");
    });
  } catch (error) {
    console.error("Failed to start server:", error.message);
    process.exit(1);
  }
};

start();
