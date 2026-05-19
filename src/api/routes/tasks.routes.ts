/**
 * api/routes/tasks.routes.ts
 * /api/tasks 경로에 대한 라우트를 정의한다.
 *
 * 엔드포인트:
 *   POST   /api/tasks          - 새 업무 생성 (워크플로우 자동 시작)
 *   GET    /api/tasks/:id      - 업무 상태 조회
 */

import { Router } from "express";
import { TaskController } from "../controllers/TaskController";

const router = Router();
const controller = new TaskController();

router.post("/", (req, res) => controller.create(req, res));
router.get("/:id", (req, res) => controller.getById(req, res));

export default router;
