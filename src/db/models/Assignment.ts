/**
 * db/models/Assignment.ts
 * assignments 테이블의 레코드 구조를 정의한다.
 * MatcherAgent가 결정한 최종 담당자 배정 결과를 저장한다.
 *
 * 테이블 컬럼:
 *   id           UUID PK
 *   task_id      UUID FK → tasks.id
 *   member_id    VARCHAR
 *   score        SMALLINT (0~100)
 *   reason       TEXT     (추천 사유)
 *   assigned_at  TIMESTAMP
 */

export interface AssignmentRecord {
  id: string;
  taskId: string;
  memberId: string;
  score: number;
  reason: string;
  assignedAt: string;
}
