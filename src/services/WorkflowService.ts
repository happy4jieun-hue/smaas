/**
 * services/WorkflowService.ts
 * 워크플로우 실행 요청을 OrchestratorAgent에 위임하고,
 * 실행 결과를 WorkflowRepository를 통해 DB에 저장하는 역할을 한다.
 * 워크플로우 조회 API에서도 이 서비스를 통해 데이터를 가져온다.
 */

/**
 * services/WorkflowService.ts
 * - workflow 먼저 생성 (pending)
 * - AI 실행은 백그라운드에서 수행 (non-blocking)
 * - 완료/실패 시 DB 업데이트
 */

import { v4 as uuidv4 } from "uuid";
import { OrchestratorAgent } from "../agents/orchestrator/OrchestratorAgent";
import { WorkflowRepository } from "../db/repositories/WorkflowRepository";
import { TaskInput } from "../types/task.types";
import { AgentContext } from "../types/workflow.types";
import { WorkflowRecord } from "../db/models/Workflow";

export class WorkflowService {
  private orchestrator: OrchestratorAgent;
  private workflowRepo: WorkflowRepository;

  constructor() {
    this.orchestrator = new OrchestratorAgent();
    this.workflowRepo = new WorkflowRepository();
  }

  /**
   * 🔥 workflow 생성 → 비동기 실행
   */
  async startWorkflow(taskId: string, input: TaskInput): Promise<void> {
    const workflowId = uuidv4();
    const now = new Date().toISOString();

    const initialContext: AgentContext = {
      workflowId,
      taskId,
      input,
      status: "pending",
      steps: {},
      errors: [],
      startedAt: now,
      updatedAt: now,
    };

    // 1️⃣ 먼저 생성 (404 방지)
    await this.workflowRepo.createWorkflow({
      id: workflowId,
      taskId,
      status: "pending",
      context: initialContext,
    });

    // 2️⃣ 백그라운드 실행 (await ❌)
    this.runAsync(workflowId, taskId, input);
  }

  /**
   * 🔥 실제 workflow 실행
   */
  private async runAsync(
    workflowId: string,
    taskId: string,
    input: TaskInput
  ): Promise<void> {
    try {
      const context = await this.orchestrator.run(input, {
        workflowId,
        taskId,
      });

      // 성공 업데이트
      await this.workflowRepo.updateWorkflow(
        workflowId,
        context.status,
        context
      );
    } catch (err) {
      console.error("[WorkflowService] runAsync error:", err);

      // 🔥 타입 안전한 실패 context 생성
      const now = new Date().toISOString();

      const failedContext: AgentContext = {
        workflowId,
        taskId,
        input,
        status: "failed",
        steps: {},
        errors: [
          {
            message: (err as Error).message,
            agentName: "workflow-service",
            timestamp: now,
          },
        ],
        startedAt: now,
        updatedAt: now,
      };

      await this.workflowRepo.updateWorkflow(
        workflowId,
        "failed",
        failedContext
      );
    }
  }

  /**
   * Workflow 조회 (프론트에서 사용)
   */
  async getWorkflowByTaskId(taskId: string): Promise<WorkflowRecord | null> {
    return this.workflowRepo.findByTaskId(taskId);
  }
}