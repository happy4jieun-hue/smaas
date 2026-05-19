import type { AssignmentPatch, SubTaskAssignmentRecord } from "../types";

const BASE = "/api";

export async function getAssignments(taskId: string): Promise<SubTaskAssignmentRecord[]> {
  const res = await fetch(`${BASE}/tasks/${taskId}/assignments`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function patchAssignment(
  assignmentId: string,
  patch: AssignmentPatch
): Promise<SubTaskAssignmentRecord> {
  const res = await fetch(`${BASE}/assignments/${assignmentId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function approveAllAssignments(taskId: string): Promise<{ approvedCount: number }> {
  const res = await fetch(`${BASE}/tasks/${taskId}/assignments/approve-all`, { method: "POST" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
