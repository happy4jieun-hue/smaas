/**
 * db/models/WorkflowStep.ts
 * workflow_steps 테이블의 레코드 구조를 정의한다.
 * 각 에이전트 단계의 실행 결과를 개별 행으로 저장한다.
 * UNIQUE(workflow_id, step_name) 으로 워크플로우 당 단계 1회 저장을 보장한다.
 *
 * 테이블 컬럼:
 *   id          UUID PK
 *   workflow_id UUID FK → workflows.id
 *   step_name   agent_name ENUM  (analyzer | planner | matcher | validator | notifier)
 *   step_status step_status ENUM (success | failed)
 *   input       JSONB  (해당 에이전트가 받은 AgentContext 스냅샷)
 *   output      JSONB  (해당 에이전트의 실행 결과, 실패 시 NULL)
 *   error       TEXT   (nullable)
 *   created_at  TIMESTAMP
 */

import { AgentStepName } from "../../types/agent.types";
export type { AgentStepName };

export interface WorkflowStepRecord {
  id: string;
  workflowId: string;
  stepName: AgentStepName;
  stepStatus: "success" | "failed";
  input: object;
  output: object | null;
  error: string | null;
  createdAt: string;
}
