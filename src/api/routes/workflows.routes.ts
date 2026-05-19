/**
 * api/routes/workflows.routes.ts
 * /api/workflows 경로에 대한 라우트를 정의한다.
 *
 * 엔드포인트:
 *   GET    /api/workflows/:taskId   - task_id로 워크플로우 진행 상태 조회
 */

import { Router } from "express";
import { WorkflowController } from "../controllers/WorkflowController";

const router = Router();
const controller = new WorkflowController();

router.get("/:taskId", (req, res) => controller.getByTaskId(req, res));

export default router;
