import express from "express";
import cors from "cors";
import { config } from "./config";
import taskRoutes from "./api/routes/tasks.routes";
import workflowRoutes from "./api/routes/workflows.routes";
import { errorMiddleware } from "./api/middlewares/error.middleware";

const app = express();

// ✅ 핵심
app.use(cors());
app.use(express.json());

// ── 헬스 체크 ─────────────────────────────
app.get("/health", (_req, res) => res.json({ status: "ok" }));

// ── 라우터 ────────────────────────────────
app.use("/api/tasks", taskRoutes);
app.use("/api/workflows", workflowRoutes);

// ── 에러 핸들러 ───────────────────────────
app.use(errorMiddleware);

// ── 서버 시작 ─────────────────────────────
app.listen(config.port, () => {
  console.log(`[Smaas] Server running on port ${config.port}`);
});

export default app;