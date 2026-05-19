/**
 * types/task.types.ts
 * Task(업무) 도메인과 관련된 모든 타입을 정의한다.
 * DB 모델, API 요청/응답, 에이전트 입출력에서 공통으로 사용한다.
 */

export type TaskStatus =
  | "pending"    // 생성됨, 아직 처리 전
  | "running"    // 워크플로우 진행 중
  | "completed"  // 정상 완료
  | "failed";    // 처리 중 오류 발생

export type TaskComplexity = 1 | 2 | 3 | 4 | 5; // 1: 단순 ~ 5: 매우 복잡

export interface TaskInput {
  title: string;
  description: string;
  requesterId: string; // 업무를 요청한 사용자 ID
  deadline?: string;   // ISO 8601
}

export interface Task extends TaskInput {
  id: string;
  status: TaskStatus;
  createdAt: string;
  updatedAt: string;
}
