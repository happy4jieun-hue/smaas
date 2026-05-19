/**
 * db/repositories/WorkflowRepository.ts
 * workflows, workflow_steps, assignments 테이블에 대한 쿼리를 캡슐화한다.
 * Orchestrator가 워크플로우 상태를 저장하고 조회할 때 사용한다.
 */

import { pool } from "../pool";
import { WorkflowRecord } from "../models/Workflow";
import { WorkflowStepRecord } from "../models/WorkflowStep";
import { AssignmentRecord } from "../models/Assignment";
import { v4 as uuidv4 } from "uuid";

export class WorkflowRepository {
  async createWorkflow(record: Omit<WorkflowRecord, "createdAt" | "updatedAt">): Promise<WorkflowRecord> {
    const { rows } = await pool.query<WorkflowRecord>(
      `INSERT INTO workflows (id, task_id, status, context)
       VALUES ($1, $2, $3, $4)
       RETURNING id,
                 task_id AS "taskId",
                 status,
                 context,
                 created_at AS "createdAt",
                 updated_at AS "updatedAt"`,
      [record.id, record.taskId, record.status, JSON.stringify(record.context)]
    );
    return rows[0];
  }

  async updateWorkflow(id: string, status: string, context: object): Promise<void> {
    await pool.query(
      `UPDATE workflows SET status = $1, context = $2, updated_at = NOW() WHERE id = $3`,
      [status, JSON.stringify(context), id]
    );
  }

  async createStep(record: Omit<WorkflowStepRecord, "id" | "createdAt">): Promise<WorkflowStepRecord> {
    const id = uuidv4();
    const { rows } = await pool.query<WorkflowStepRecord>(
      `INSERT INTO workflow_steps (id, workflow_id, step_name, step_status, input, output, error)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT (workflow_id, step_name)
         DO UPDATE SET
           step_status = EXCLUDED.step_status,
           input       = EXCLUDED.input,
           output      = EXCLUDED.output,
           error       = EXCLUDED.error,
           created_at  = NOW()
       RETURNING id,
                 workflow_id  AS "workflowId",
                 step_name    AS "stepName",
                 step_status  AS "stepStatus",
                 input, output, error,
                 created_at   AS "createdAt"`,
      [
        id, record.workflowId, record.stepName, record.stepStatus,
        JSON.stringify(record.input),
        record.output ? JSON.stringify(record.output) : null,
        record.error ?? null,
      ]
    );
    return rows[0];
  }

  async createAssignment(record: Omit<AssignmentRecord, "id">): Promise<AssignmentRecord> {
    const id = uuidv4();
    const { rows } = await pool.query<AssignmentRecord>(
      `INSERT INTO assignments (id, task_id, member_id, score, reason, assigned_at)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id,
                 task_id AS "taskId",
                 member_id AS "memberId",
                 score, reason,
                 assigned_at AS "assignedAt"`,
      [id, record.taskId, record.memberId, record.score, record.reason, record.assignedAt]
    );
    return rows[0];
  }

  async findByTaskId(taskId: string): Promise<WorkflowRecord | null> {
    const { rows } = await pool.query<WorkflowRecord>(
      `SELECT id,
              task_id AS "taskId",
              status,
              context,
              created_at AS "createdAt",
              updated_at AS "updatedAt"
       FROM workflows WHERE task_id = $1
       ORDER BY created_at DESC LIMIT 1`,
      [taskId]
    );
    return rows[0] ?? null;
  }
}
