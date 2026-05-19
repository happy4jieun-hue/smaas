/**
 * db/models/Workflow.ts
 * workflows 테이블의 레코드 구조를 정의한다.
 * 하나의 Task에 대해 생성된 워크플로우 인스턴스 전체 상태를 저장한다.
 *
 * 테이블 컬럼:
 *   id         UUID PK
 *   task_id    UUID FK → tasks.id
 *   status     VARCHAR  (WorkflowStatus)
 *   context    JSONB    (AgentContext 전체를 직렬화)
 *   created_at TIMESTAMP
 *   updated_at TIMESTAMP
 */

export interface WorkflowRecord {
  id: string;
  taskId: string;
  status: string;
  context: object; // JSONB → AgentContext
  createdAt: string;
  updatedAt: string;
}
