/**
 * api/controllers/WorkflowController.ts
 * 워크플로우 조회 관련 HTTP 요청을 처리한다.
 * WorkflowService에 위임해 에이전트 실행 진행 상황을 반환한다.
 */

import { Request, Response } from "express";
import { WorkflowService } from "../../services/WorkflowService";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export class WorkflowController {
  private workflowService: WorkflowService;

  constructor() {
    this.workflowService = new WorkflowService();
  }

  /** GET /api/workflows/:taskId */
  async getByTaskId(req: Request, res: Response): Promise<void> {
    const { taskId } = req.params;

    // UUID 형식 검증 — PostgreSQL "invalid input syntax for type uuid" 방지
    if (!UUID_RE.test(taskId)) {
      console.warn(`[WorkflowController] invalid taskId format: "${taskId}" (length=${taskId?.length})`);
      res.status(400).json({ error: `Invalid taskId: expected UUID, got "${taskId}"` });
      return;
    }

    try {
      const record = await this.workflowService.getWorkflowByTaskId(taskId);
      if (!record) {
        res.status(404).json({ error: "Workflow not found" });
        return;
      }
      res.json(record);
    } catch (err) {
      res.status(500).json({ error: (err as Error).message });
    }
  }
}
