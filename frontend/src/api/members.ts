import type { MemberInput, MemberRecord, MemberUpdate } from "../types";

const BASE = "/api";

export async function getMembers(): Promise<MemberRecord[]> {
  const res = await fetch(`${BASE}/members`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function createMember(data: MemberInput): Promise<MemberRecord> {
  const res = await fetch(`${BASE}/members`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function updateMember(id: string, data: MemberUpdate): Promise<MemberRecord> {
  const res = await fetch(`${BASE}/members/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export async function deleteMember(id: string): Promise<void> {
  const res = await fetch(`${BASE}/members/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
}
