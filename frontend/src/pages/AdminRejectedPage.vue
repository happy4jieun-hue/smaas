<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

interface RejectedItem {
  id: string;
  taskId: string;
  taskTitle: string;
  subTaskTitle: string;
  subTaskDescription: string | null;
  priority: string | null;
  rejectionReason: string | null;
  rejectedAt: string | null;
  approvedMemberId: string | null;
  approvedMemberName: string;
  reassignmentCount: number;
  suggestedRole: string | null; suggestedReason: string | null;
}

interface Member { id: string; name: string; }

const items      = ref<RejectedItem[]>([]);
const members    = ref<Member[]>([]);
const loading    = ref(false);
const saving     = ref<string | null>(null);
const errMsg     = ref("");

// 재배정 모달
const modal        = ref<RejectedItem | null>(null);
const selectedId   = ref("");
const reassignMemo = ref("");


const managerId = localStorage.getItem("smaas_member_id") ?? "";

const PRIORITY_COLOR: Record<string, string> = {
  high: "#ef4444", medium: "#f59e0b", low: "#6b7280",
};

async function load() {
  loading.value = true;
  errMsg.value = "";
  try {
    const [rRes, mRes] = await Promise.all([
      fetch("/api/admin/rejected"),
      fetch("/api/members"),
    ]);
    items.value   = await rRes.json();
    members.value = await mRes.json();
  } finally {
    loading.value = false;
  }
}

function openModal(item: RejectedItem) {
  modal.value      = item;
  // AI 추천이 있으면 선택, 없으면 기존 담당자
  const ai = aiResult.value[item.id];
  selectedId.value = ai?.recommendedId || item.approvedMemberId || "";
  reassignMemo.value = "";
}

function closeModal() {
  modal.value = null;
  selectedId.value = "";
  reassignMemo.value = "";
}

async function submitReassign() {
  if (!modal.value || !selectedId.value) return;
  saving.value = modal.value.id;
  errMsg.value = "";
  try {
    const res = await fetch(
      `/api/admin/assignments/${modal.value.id}/reassign?manager_id=${managerId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ newMemberId: selectedId.value, memo: reassignMemo.value || null }),
      }
    );
    if (!res.ok) throw new Error(await res.text());
    closeModal();
    await load();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    saving.value = null;
  }
}

function memberName(id: string) {
  return members.value.find(m => m.id === id)?.name ?? id;
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header">
      <button class="back-btn" @click="router.push('/admin')">← 대시보드</button>
      <h1>반려 업무 재배정</h1>
      <button class="btn-refresh" @click="load">새로고침</button>
    </div>

    <div v-if="errMsg" class="err">{{ errMsg }}</div>
    <div v-if="loading" class="empty">로딩 중…</div>
    <div v-else-if="items.length === 0" class="empty">반려된 업무가 없습니다.</div>

    <div v-else class="list">
      <div v-for="item in items" :key="item.id" class="card">
        <div class="card-head">
          <div class="card-info">
            <div class="task-link" @click="router.push(`/tasks/${item.taskId}/assignments`)">
              📋 {{ item.taskTitle }}
            </div>
            <div class="subtask-title">{{ item.subTaskTitle }}</div>
            <div v-if="item.subTaskDescription" class="subtask-desc">{{ item.subTaskDescription }}</div>
          </div>
          <div class="card-badges">
            <span v-if="item.priority" class="p-badge"
              :style="{ background: PRIORITY_COLOR[item.priority] + '20', color: PRIORITY_COLOR[item.priority] }">
              {{ item.priority }}
            </span>
            <span class="member-chip">👤 {{ item.approvedMemberName || "—" }}</span>
            <span v-if="item.reassignmentCount > 0" class="reassign-cnt">재배정 {{ item.reassignmentCount }}회</span>
          </div>
        </div>

        <!-- 반려 사유 -->
        <div class="rejection-box">
          <span class="rejection-label">반려 사유</span>
          {{ item.rejectionReason || "—" }}
          <span v-if="item.rejectedAt" class="rejected-date">{{ item.rejectedAt.slice(0, 10) }}</span>
        </div>

        <!-- AI 추천 역할 -->
        <div v-if="item.suggestedRole" class="ai-result">
          <span class="ai-label">AI 추천 역할</span>
          <span class="role-badge-sm">{{ item.suggestedRole }}</span>
          <span v-if="item.suggestedReason" class="ai-reason">— {{ item.suggestedReason }}</span>
        </div>

        <!-- 액션 -->
        <div class="card-actions">
          <button class="btn-reassign" @click="openModal(item)">
            재배정 →
          </button>
        </div>
      </div>
    </div>

    <!-- 재배정 모달 -->
    <div v-if="modal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2>재배정</h2>
        <div class="modal-info">
          <b>{{ modal.subTaskTitle }}</b> 업무를 누구에게 배정하시겠습니까?
        </div>

        <div class="modal-field">
          <label>담당자 선택</label>
          <select v-model="selectedId">
            <option value="">— 선택 —</option>
            <option v-for="m in members" :key="m.id" :value="m.id">
              {{ m.name }}{{ m.id === modal.approvedMemberId ? " (기존 담당자)" : "" }}
              {{ aiResult[modal.id]?.recommendedId === m.id ? " ⭐ AI 추천" : "" }}
            </option>
          </select>
        </div>

        <div class="modal-field">
          <label>메모 (선택)</label>
          <textarea v-model="reassignMemo" rows="2" placeholder="재배정 사유나 지시사항을 입력하세요." />
        </div>

        <div v-if="errMsg" class="err">{{ errMsg }}</div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="closeModal">취소</button>
          <button
            class="btn-reassign"
            :disabled="!!saving || !selectedId"
            @click="submitReassign"
          >
            {{ saving ? "처리 중…" : "재배정 확정" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 900px; margin: 0 auto; padding: 32px 24px; }
.header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
h1 { font-size: 22px; font-weight: 700; margin: 0; flex: 1; }
.back-btn { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 13px; padding: 0; }
.btn-refresh { padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }
.err { background: #fef2f2; color: #b91c1c; border-radius: 6px; padding: 8px 12px; font-size: 13px; margin-bottom: 14px; }
.empty { text-align: center; padding: 60px; color: #9ca3af; }

.list { display: flex; flex-direction: column; gap: 14px; }
.card { background: #fff; border: 1px solid #fca5a5; border-radius: 10px; padding: 18px; }

.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.card-info { flex: 1; }
.task-link { font-size: 12px; color: #2563eb; cursor: pointer; margin-bottom: 4px; }
.task-link:hover { text-decoration: underline; }
.subtask-title { font-size: 15px; font-weight: 600; color: #111827; }
.subtask-desc { font-size: 13px; color: #6b7280; margin-top: 3px; }
.card-badges { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; flex-shrink: 0; }
.p-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.member-chip { font-size: 12px; background: #f3f4f6; padding: 3px 8px; border-radius: 20px; }
.reassign-cnt { font-size: 11px; background: #fef3c7; color: #92400e; padding: 2px 7px; border-radius: 4px; }

.rejection-box { background: #fef2f2; border-radius: 6px; padding: 10px 12px; font-size: 13px; color: #7f1d1d; margin-bottom: 10px; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.rejection-label { font-weight: 700; color: #ef4444; flex-shrink: 0; }
.rejected-date { font-size: 11px; color: #9ca3af; margin-left: auto; }

.ai-result { background: #f0fdf4; border-radius: 6px; padding: 10px 12px; font-size: 13px; margin-bottom: 10px; }
.ai-label { font-weight: 700; color: #059669; margin-right: 6px; }
.role-badge-sm { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; background: #dbeafe; color: #1d4ed8; }
.ai-reason { font-size: 12px; color: #6b7280; }

.card-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 10px; }
.btn-reassign { padding: 7px 18px; background: #2563eb; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 13px; font-weight: 600; }
.btn-reassign:disabled { opacity: 0.5; cursor: not-allowed; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 460px; max-width: 95vw; }
.modal h2 { font-size: 18px; font-weight: 700; margin: 0 0 12px; }
.modal-info { font-size: 14px; color: #4b5563; margin-bottom: 16px; }
.modal-field { margin-bottom: 14px; }
.modal-field label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 5px; }
.modal-field select, .modal-field textarea { width: 100%; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px; }
.btn-cancel { padding: 8px 18px; border: 1px solid #d1d5db; border-radius: 7px; background: #fff; cursor: pointer; font-size: 14px; }
</style>
