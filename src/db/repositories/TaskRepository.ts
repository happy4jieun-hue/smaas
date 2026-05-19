/**
 * db/repositories/TaskRepository.ts
 * tasks 테이블에 대한 CRUD 쿼리를 캡슐화한다.
 * Service 레이어는 SQL을 직접 작성하지 않고 이 클래스를 통해 데이터에 접근한다.
 */

import { pool } from "../pool";
import { TaskRecord } from "../models/Task";

export class TaskRepository {
  async create(task: Omit<TaskRecord, "createdAt" | "updatedAt">): Promise<TaskRecord> {
    const { rows } = await pool.query<TaskRecord>(
      `INSERT INTO tasks (id, title, description, requester_id, deadline, status)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id, title, description,
                 requester_id AS "requesterId",
                 deadline,
                 status,
                 created_at AS "createdAt",
                 updated_at AS "updatedAt"`,
      [task.id, task.title, task.description, task.requesterId, task.deadline ?? null, task.status]
    );
    return rows[0];
  }

  async findById(id: string): Promise<TaskRecord | null> {
    const { rows } = await pool.query<TaskRecord>(
      `SELECT id, title, description,
              requester_id AS "requesterId",
              deadline,
              status,
              created_at AS "createdAt",
              updated_at AS "updatedAt"
       FROM tasks WHERE id = $1`,
      [id]
    );
    return rows[0] ?? null;
  }

  async updateStatus(id: string, status: string): Promise<void> {
    await pool.query(
      `UPDATE tasks SET status = $1, updated_at = NOW() WHERE id = $2`,
      [status, id]
    );
  }
}
