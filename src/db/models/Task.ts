/**
 * db/models/Task.ts
 * tasks 테이블의 레코드 구조를 정의한다.
 * 사용자가 등록한 원본 업무 요청을 저장한다.
 *
 * 테이블 컬럼:
 *   id          UUID PK
 *   title       VARCHAR
 *   description TEXT
 *   requester_id VARCHAR
 *   deadline    TIMESTAMP (nullable)
 *   status      VARCHAR  (pending | running | completed | failed)
 *   created_at  TIMESTAMP
 *   updated_at  TIMESTAMP
 */

export interface TaskRecord {
  id: string;
  title: string;
  description: string;
  requesterId: string;
  deadline: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}
