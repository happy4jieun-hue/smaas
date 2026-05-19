/**
 * api/controllers/TaskController.ts
 * HTTP 요청/응답 처리를 담당한다.
 * 입력 유효성 검사 후 TaskService에 위임하고 결과를 JSON으로 반환한다.
 * 비즈니스 로직은 포함하지 않는다.
 */

import { Request, Response } from "express";
import { TaskService } from "../../services/TaskService";


export class TaskController {
  private taskService: TaskService;

  constructor() {
    this.taskService = new TaskService();
  }

  /** POST /api/tasks */
  async create(req: Request, res: Response): Promise<void> {
    const { title, description, requesterId, deadline } = req.body ?? {};

  

    if (!title || !description || !requesterId) {
      res.status(400).json({ error: "title, description, requesterId are required" });
      return;
    }

    try {


      const task = await this.taskService.createTask({
        title,
        description,
        requesterId,
        deadline,
      });

      console.log("✅ TASK CREATED:", task); // 👈 추가

      res.status(201).json(task);
    } catch (err) {
      console.error("❌ TASK ERROR:", err); // 👈 제일 중요

      const status = (err as { status?: number }).status ?? 500;
      res.status(status).json({ error: (err as Error).message });
    }
  }

  /** GET /api/tasks/:id */
  async getById(req: Request, res: Response): Promise<void> {
    try {
      const task = await this.taskService.getTaskById(req.params.id);
      res.json(task);
    } catch (err) {
      const status = (err as { status?: number }).status ?? 500;
      res.status(status).json({ error: (err as Error).message });
    }
  }
}
