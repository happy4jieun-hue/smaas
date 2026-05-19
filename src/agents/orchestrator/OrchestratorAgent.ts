/**
 * agents/orchestrator/OrchestratorAgent.ts
 * 워크플로우의 진입점이자 전체 흐름을 제어하는 에이전트.
 * 각 에이전트를 순서대로 호출하고, 실패 시 재시도 또는 폴백을 결정한다.
 * 에이전트끼리 직접 통신하지 않고 반드시 이 Orchestrator를 통해 흐름이 이어진다.
 */

import { AgentContext } from "../../types/workflow.types";
import { TaskInput } from "../../types/task.types";
import { WorkflowEngine } from "./WorkflowEngine";
import { v4 as uuidv4 } from "uuid";

export class OrchestratorAgent {
  private engine: WorkflowEngine;

  constructor() {
    this.engine = new WorkflowEngine();
  }

  /**
   * 새 업무를 받아 전체 워크플로우를 실행하고 최종 컨텍스트를 반환한다.
   * @param input    태스크 입력
   * @param ids      WorkflowService에서 사전 생성한 workflowId/taskId (없으면 자체 생성)
   */
  async run(
    input: TaskInput,
    ids?: { workflowId: string; taskId: string }
  ): Promise<AgentContext> {
    const context: AgentContext = {
      workflowId: ids?.workflowId ?? uuidv4(),
      taskId:     ids?.taskId     ?? uuidv4(),
      input,
      status: "pending",
      steps: {},
      errors: [],
      startedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    return this.engine.execute(context);
  }
}
