import type { WorkflowRecord } from "../types";

const BASE = "/api";

export async function getWorkflowByTaskId(taskId: string): Promise<WorkflowRecord> {
  const res = await fetch(`${BASE}/workflows/${taskId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
