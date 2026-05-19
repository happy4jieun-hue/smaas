<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

interface PlanItem {
  planId: string;
  assignmentId: string;
  taskId: string;
  taskTitle: string;
  subTaskTitle: string;
  priority: string | null;
  memberId: string;
  memberName: string;
  content: string;
  status: string;
  feedback: string | null;
  submittedAt: string;
  reviewedAt: string | null;
}

const plans   = ref<PlanItem[]>([]);
const loading = ref(true);
const saving  = ref<string | null>(null);  // planId being saved
const errMsg  = ref("");

// 모달 상태
const modal   = ref<PlanItem | null>(null);
const action  = ref<"approve" | "reject" | null>(null);
const feedback = ref("");

const PRIORITY_COLOR: Record<string, string> = {
  high: "#ef4444", medium: "#f59e0b", low: "#6b7280",
};

async function load() {
  loading.value = true;
  try {
    const res = await fetch("/api/admin/plans");
    plans.value = await res.json();
  } finally {
    loading.value = false;
  }
}

function openModal(plan: PlanItem, act: "approve" | "reject") {
  modal.value  = plan;
  action.value = act;
  feedback.value = plan.feedback ?? "";
}

function closeModal() {
  modal.value  = null;
  action.value = null;
  feedback.value = "";
}

async function submitAction() {
  if (!modal.value || !action.value) return;
  saving.value = modal.value.planId;
  errMsg.value = "";
  try {
    const body: Record<string, unknown> = {
      status: action.value === "approve" ? "approved" : "rejected",
    };
    if (feedback.value.trim()) body.feedback = feedback.value.trim();

    const res = await fetch(`/api/work-plans/${modal.value.planId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    closeModal();
    await load();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    saving.value = null;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header">
      <div class="breadcrumb">
        <button class="back-btn" @click="router.push('/admin')">← 대시보드</button>
      </div>
      <h1>계획 승인</h1>
      <button class="btn-refresh" @click="load">새로고침</button>
    </div>

    <div v-if="loading" class="loading">로딩 중…</div>

    <div v-else-if="plans.length === 0" class="empty">
      검토 대기 중인 업무 계획이 없습니다.
    </div>

    <div v-else class="plan-list">
      <div v-for="p in plans" :key="p.planId" class="plan-card">
        <!-- 카드 헤더 -->
        <div class="card-head">
          <div class="card-titles">
            <div class="task-title" @click="router.push(`/tasks/${p.taskId}/assignments`)" title="배정 검토로 이동">
              📋 {{ p.taskTitle }}
            </div>
            <div class="subtask-title">{{ p.subTaskTitle }}</div>
          </div>
          <div class="card-meta">
            <span class="priority-badge" v-if="p.priority" :style="{ background: PRIORITY_COLOR[p.priority] + '20', color: PRIORITY_COLOR[p.priority] }">
              {{ p.priority }}
            </span>
            <span class="member-chip">👤 {{ p.memberName }}</span>
            <span class="date-chip">{{ p.submittedAt.slice(0, 10) }} 제출</span>
          </div>
        </div>

        <!-- 계획 내용 -->
        <div class="plan-content">{{ p.content }}</div>

        <!-- 기존 피드백 (재검토 케이스) -->
        <div v-if="p.feedback" class="old-feedback">이전 피드백: {{ p.feedback }}</div>

        <!-- 액션 버튼 -->
        <div class="card-actions">
          <button class="btn-approve" :disabled="saving === p.planId" @click="openModal(p, 'approve')">
            ✓ 승인
          </button>
          <button class="btn-reject" :disabled="saving === p.planId" @click="openModal(p, 'reject')">
            ✕ 반려
          </button>
        </div>
      </div>
    </div>

    <!-- 승인/반려 모달 -->
    <div v-if="modal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <h2>{{ action === "approve" ? "계획 승인" : "계획 반려" }}</h2>
        <div class="modal-info">
          <b>{{ modal.memberName }}</b>의 <b>{{ modal.subTaskTitle }}</b> 계획을
          {{ action === "approve" ? "승인" : "반려" }}합니다.
        </div>
        <div class="modal-field">
          <label>{{ action === "approve" ? "코멘트 (선택)" : "반려 사유 (선택)" }}</label>
          <textarea v-model="feedback" rows="3" :placeholder="action === 'reject' ? '반려 사유를 입력하면 worker에게 전달됩니다.' : '승인 코멘트를 남길 수 있습니다.'" />
        </div>
        <div v-if="errMsg" class="err">{{ errMsg }}</div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="closeModal">취소</button>
          <button
            :class="action === 'approve' ? 'btn-approve' : 'btn-reject'"
            :disabled="!!saving"
            @click="submitAction"
          >
            {{ saving ? "처리 중…" : (action === "approve" ? "승인 확정" : "반려 확정") }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 860px; margin: 0 auto; padding: 32px 24px; }
.header { display: flex; align-items: center; gap: 16px; margin-bottom: 28px; }
h1 { font-size: 22px; font-weight: 700; margin: 0; flex: 1; }
.breadcrumb { flex-shrink: 0; }
.back-btn { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 13px; padding: 0; }
.btn-refresh { padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }
.loading, .empty { text-align: center; padding: 60px; color: #9ca3af; }

.plan-list { display: flex; flex-direction: column; gap: 16px; }
.plan-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; }

.card-head { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 14px; gap: 12px; }
.card-titles { flex: 1; }
.task-title { font-size: 12px; color: #2563eb; cursor: pointer; margin-bottom: 4px; }
.task-title:hover { text-decoration: underline; }
.subtask-title { font-size: 16px; font-weight: 600; color: #111827; }
.card-meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; flex-shrink: 0; }

.priority-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.member-chip { font-size: 12px; background: #f3f4f6; color: #374151; padding: 3px 8px; border-radius: 20px; }
.date-chip { font-size: 12px; color: #9ca3af; }

.plan-content {
  background: #f9fafb; border-radius: 6px; padding: 14px;
  font-size: 14px; line-height: 1.7; white-space: pre-wrap;
  color: #374151; margin-bottom: 12px;
}
.old-feedback { font-size: 13px; color: #92400e; background: #fffbeb; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; }

.card-actions { display: flex; gap: 10px; }
.btn-approve { padding: 8px 20px; background: #10b981; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-approve:hover:not(:disabled) { background: #059669; }
.btn-approve:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-reject { padding: 8px 20px; background: #fff; color: #ef4444; border: 1px solid #ef4444; border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-reject:hover:not(:disabled) { background: #fef2f2; }
.btn-reject:disabled { opacity: 0.5; cursor: not-allowed; }

/* 모달 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 460px; max-width: 95vw; }
.modal h2 { font-size: 18px; font-weight: 700; margin: 0 0 14px; }
.modal-info { font-size: 14px; color: #4b5563; margin-bottom: 16px; line-height: 1.5; }
.modal-field label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.modal-field textarea { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; resize: vertical; box-sizing: border-box; }
.err { background: #fef2f2; color: #b91c1c; border-radius: 6px; padding: 8px 12px; font-size: 13px; margin-top: 10px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px; }
.btn-cancel { padding: 8px 18px; border: 1px solid #d1d5db; border-radius: 7px; background: #fff; cursor: pointer; font-size: 14px; }
</style>
