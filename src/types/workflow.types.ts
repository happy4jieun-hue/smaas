/**
 * types/workflow.types.ts
 * 워크플로우 실행 흐름과 관련된 타입을 정의한다.
 * Orchestrator가 각 에이전트 결과를 AgentContext에 누적하며 상태를 관리한다.
 */

import {
  AnalysisResult,
  MatchResult,
  NotificationResult,
  PlanResult,
  ValidationResult,
} from "./agent.types";
import { TaskInput } from "./task.types";

export type WorkflowStatus =
  | "pending"
  | "analyzing"
  | "planning"
  | "matching"
  | "validating"
  | "saving"
  | "notifying"
  | "completed"
  | "failed";

// 에이전트 간 공유되는 워크플로우 컨텍스트
export interface AgentContext {
  workflowId: string;
  taskId: string;
  input: TaskInput;
  status: WorkflowStatus;
  steps: {
    analyzed?: AnalysisResult;
    planned?: PlanResult;
    matched?: MatchResult;
    validated?: ValidationResult;
    notified?: NotificationResult;
  };
  errors: AgentError[];
  startedAt: string;
  updatedAt: string;
}

export interface AgentError {
  agentName: string;
  message: string;
  timestamp: string;
}

// DB에 저장되는 워크플로우 스냅샷
export interface WorkflowRecord {
  id: string;
  taskId: string;
  status: WorkflowStatus;
  context: AgentContext; // JSON 컬럼으로 직렬화
  createdAt: string;
  updatedAt: string;
}
