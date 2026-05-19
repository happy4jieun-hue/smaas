<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const route  = useRoute();
const router = useRouter();
const assignmentId = route.params.id as string;
const memberId = localStorage.getItem("smaas_member_id") ?? "";

interface Assignment {
  id: string; taskId: string; subTaskTitle: string; subTaskDescription: string | null;
  priority: string | null; status: string; workerStatus: string;
  approvedMemberId: string | null; approvedBy: string | null; approvedAt: string | null;
  reason: string | null; memo: string | null; candidates: any[]; updatedAt: string;
}
interface WorkPlan { id: string; content: string; status: string; feedback: string | null; submittedAt: string; }
interface WorkUpdate { id: string; content: string; progressPercent: number; updateType: string; createdAt: string; }

const assignment = ref<Assignment | null>(null);
const workPlan   = ref<WorkPlan | null>(null);
const updates    = ref<WorkUpdate[]>([]);
const loading    = ref(true);
const loadErr    = ref("");

// 폼 상태
const showPlanForm    = ref(false);
const showUpdateForm  = ref(false);
const showRejectModal = ref(false);
const planContent     = ref("");
const updateContent   = ref("");
const updatePercent   = ref(50);
const updateType      = ref<"progress" | "completion">("progress");
const rejectReason    = ref("");
const saving          = ref(false);
const errMsg          = ref("");

const WORKER_STATUS_LABEL: Record<string, string> = {
  pending_acceptance: "수락 대기", accepted: "수락됨", rejected: "반려됨",
  in_progress: "진행 중", done: "완료 보고됨",
};
const PLAN_STATUS_LABEL: Record<string, string> = {
  submitted: "검토 대기", approved: "승인됨", rejected: "반려됨",
};

async function load() {
  loading.value = true;
  loadErr.value = "";
  try {
    const [aRes, pRes, uRes] = await Promise.all([
      fetch(`/api/assignments/${assignmentId}`),
      fetch(`/api/assignments/${assignmentId}/work-plan`),
      fetch(`/api/assignments/${assignmentId}/updates`),
    ]);
    if (aRes.ok) {
      assignment.value = await aRes.json();
    } else {
      loadErr.value = `업무 정보를 불러올 수 없습니다. (${aRes.status})`;
    }
    if (pRes.ok) {
      const p = await pRes.json();
      if (p) workPlan.value = p;
    }
    if (uRes.ok) updates.value = await uRes.json();
  } catch (e: any) {
    loadErr.value = e.message ?? "알 수 없는 오류가 발생했습니다.";
  } finally {
    loading.value = false;
  }
}

async function workerAction(status: string) {
  saving.value = true; errMsg.value = "";
  try {
    const res = await fetch(`/api/assignments/${assignmentId}/worker-status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workerStatus: status }),
    });
    if (!res.ok) throw new Error(await res.text());
    await load();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    saving.value = false;
  }
}

async function submitReject() {
  if (!rejectReason.value.trim()) return;
  saving.value = true; errMsg.value = "";
  try {
    const res = await fetch(
      `/api/assignments/${assignmentId}/reject?member_id=${memberId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rejectionReason: rejectReason.value.trim() }),
      }
    );
    if (!res.ok) throw new Error(await res.text());
    rejectReason.value = "";
    showRejectModal.value = false;
    await load();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    saving.value = false;
  }
}

async function submitPlan() {
  if (!planContent.value.trim()) return;
  saving.value = true; errMsg.value = "";
  try {
    const res = await fetch(
      `/api/assignments/${assignmentId}/work-plan?member_id=${memberId}`,
      { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: planContent.value }) }
    );
    if (!res.ok) throw new Error(await res.text());
    planContent.value = ""; showPlanForm.value = false;
    await load();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    saving.value = false;
  }
}

async function submitUpdate() {
  if (!updateContent.value.trim()) return;
  saving.value = true; errMsg.value = "";
  try {
    const res = await fetch(
      `/api/assignments/${assignmentId}/updates?member_id=${memberId}`,
      { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: updateContent.value, progressPercent: updatePercent.value, updateType: updateType.value }) }
    );
    if (!res.ok) throw new Error(await res.text());
    updateContent.value = ""; showUpdateForm.value = false;
    await load();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    saving.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <button class="back-btn" @click="router.push('/my-tasks')">← 내 업무 목록</button>

    <div v-if="loading" class="loading">로딩 중…</div>

    <div v-else-if="loadErr" class="error">{{ loadErr }}</div>

    <template v-else-if="assignment">
      <!-- 업무 정보 -->
      <div class="section">
        <div class="section-top">
          <h1>{{ assignment.subTaskTitle }}</h1>
          <span class="ws-badge">{{ WORKER_STATUS_LABEL[assignment.workerStatus] ?? assignment.workerStatus }}</span>
        </div>
        <p v-if="assignment.subTaskDescription" class="desc">{{ assignment.subTaskDescription }}</p>
        <div class="meta-row">
          <span class="meta" v-if="assignment.priority">우선순위: <b>{{ assignment.priority }}</b></span>
          <span class="meta" v-if="assignment.approvedAt">배정일: {{ assignment.approvedAt.slice(0,10) }}</span>
          <span class="meta" v-if="assignment.reason">추천 사유: {{ assignment.reason }}</span>
        </div>
        <div v-if="assignment.memo" class="memo">📝 메모: {{ assignment.memo }}</div>
      </div>

      <div v-if="errMsg" class="error">{{ errMsg }}</div>

      <!-- 수락/반려 (pending_acceptance 상태) -->
      <div class="section" v-if="assignment.workerStatus === 'pending_acceptance'">
        <h2>업무 수락 여부</h2>
        <p class="hint">배정된 업무를 수락하거나 반려할 수 있습니다.</p>
        <div class="action-row">
          <button class="btn-success" :disabled="saving" @click="workerAction('accepted')">✓ 수락</button>
          <button class="btn-danger" :disabled="saving" @click="showRejectModal = true">✕ 반려</button>
        </div>
      </div>

      <!-- accepted 상태에서도 반려 가능 -->
      <div class="section" v-if="assignment.workerStatus === 'accepted'">
        <div style="display:flex; justify-content:flex-end;">
          <button class="btn-danger-sm" @click="showRejectModal = true">업무 반려</button>
        </div>
      </div>

      <!-- 업무 계획 제출 (accepted 상태, 아직 계획 없을 때) -->
      <div class="section" v-if="assignment.workerStatus === 'accepted' && !workPlan">
        <h2>업무 계획 제출</h2>
        <button class="btn-primary" @click="showPlanForm = !showPlanForm">
          {{ showPlanForm ? "취소" : "계획 작성하기" }}
        </button>
        <div v-if="showPlanForm" class="form-box">
          <textarea v-model="planContent" rows="6" placeholder="업무 계획을 작성하세요. 목표, 일정, 접근 방식 등을 포함해주세요." />
          <button class="btn-primary" :disabled="saving || !planContent.trim()" @click="submitPlan">
            {{ saving ? "제출 중…" : "제출" }}
          </button>
        </div>
      </div>

      <!-- 제출된 계획 표시 -->
      <div class="section" v-if="workPlan">
        <h2>업무 계획</h2>
        <div class="plan-status">
          상태: <b :class="'plan-' + workPlan.status">{{ PLAN_STATUS_LABEL[workPlan.status] ?? workPlan.status }}</b>
          <span class="plan-date">{{ workPlan.submittedAt.slice(0, 10) }} 제출</span>
        </div>
        <div class="plan-content">{{ workPlan.content }}</div>
        <div v-if="workPlan.feedback" class="feedback">💬 관리자 피드백: {{ workPlan.feedback }}</div>
      </div>

      <!-- 진행/완료 보고 (in_progress 상태) -->
      <div class="section" v-if="assignment.workerStatus === 'in_progress'">
        <h2>진행 보고</h2>
        <button class="btn-primary" @click="showUpdateForm = !showUpdateForm">
          {{ showUpdateForm ? "취소" : "보고 작성하기" }}
        </button>
        <div v-if="showUpdateForm" class="form-box">
          <div class="form-row">
            <label>보고 유형</label>
            <select v-model="updateType">
              <option value="progress">진행 보고</option>
              <option value="completion">완료 보고</option>
            </select>
          </div>
          <div class="form-row">
            <label>진행률 {{ updatePercent }}%</label>
            <input type="range" v-model.number="updatePercent" min="0" max="100" />
          </div>
          <textarea v-model="updateContent" rows="4" placeholder="진행 상황 또는 완료 내용을 작성해주세요." />
          <button class="btn-primary" :disabled="saving || !updateContent.trim()" @click="submitUpdate">
            {{ saving ? "제출 중…" : "제출" }}
          </button>
        </div>
      </div>

      <!-- 보고 히스토리 -->
      <div class="section" v-if="updates.length > 0">
        <h2>보고 히스토리</h2>
        <div class="update-list">
          <div v-for="u in updates" :key="u.id" class="update-item">
            <div class="update-head">
              <span :class="'update-type-' + u.updateType">
                {{ u.updateType === "completion" ? "✅ 완료 보고" : "📊 진행 보고" }}
              </span>
              <span class="update-pct">{{ u.progressPercent }}%</span>
              <span class="update-date">{{ u.createdAt.slice(0, 10) }}</span>
            </div>
            <div class="update-content">{{ u.content }}</div>
          </div>
        </div>
      </div>
    </template>

    <!-- 반려 사유 입력 모달 -->
    <div v-if="showRejectModal" class="modal-overlay" @click.self="showRejectModal = false">
      <div class="modal">
        <h2>업무 반려</h2>
        <p class="modal-desc">반려 사유를 입력해 주세요. 관리자에게 전달됩니다.</p>
        <textarea
          v-model="rejectReason"
          rows="4"
          placeholder="반려 사유를 상세히 작성해 주세요."
          class="modal-textarea"
        />
        <div v-if="errMsg" class="error">{{ errMsg }}</div>
        <div class="modal-actions">
          <button class="btn-outline" @click="showRejectModal = false; errMsg = ''">취소</button>
          <button
            class="btn-danger"
            :disabled="saving || !rejectReason.trim()"
            @click="submitReject"
          >
            {{ saving ? "처리 중…" : "반려 확정" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 720px; margin: 0 auto; padding: 32px 24px; }
.back-btn { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 14px; margin-bottom: 20px; padding: 0; }
.loading { text-align: center; padding: 60px; color: #9ca3af; }

.section { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; margin-bottom: 16px; }
.section-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
h1 { font-size: 20px; font-weight: 700; margin: 0; }
h2 { font-size: 15px; font-weight: 600; margin: 0 0 12px; }
.ws-badge { flex-shrink: 0; padding: 4px 10px; border-radius: 5px; font-size: 12px; font-weight: 600; background: #eff6ff; color: #2563eb; }

.desc { color: #4b5563; font-size: 14px; line-height: 1.6; margin: 0 0 12px; }
.meta-row { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 8px; }
.meta { font-size: 13px; color: #6b7280; }
.meta b { color: #1f2937; }
.memo { font-size: 13px; color: #92400e; background: #fffbeb; padding: 8px 12px; border-radius: 6px; margin-top: 8px; }
.hint { font-size: 13px; color: #6b7280; margin-bottom: 12px; }
.error { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; padding: 10px 14px; border-radius: 6px; margin-bottom: 14px; font-size: 13px; }

.action-row { display: flex; gap: 10px; }
.btn-success { padding: 10px 24px; background: #10b981; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-success:hover { background: #059669; }
.btn-danger { padding: 10px 24px; background: #fff; color: #ef4444; border: 1px solid #ef4444; border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-danger:hover:not(:disabled) { background: #fef2f2; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger-sm { padding: 5px 12px; background: #fff; color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; }
.btn-danger-sm:hover { background: #fef2f2; }
.btn-outline { padding: 8px 18px; border: 1px solid #d1d5db; border-radius: 7px; background: #fff; cursor: pointer; font-size: 14px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 460px; max-width: 95vw; }
.modal h2 { font-size: 18px; font-weight: 700; margin: 0 0 8px; }
.modal-desc { font-size: 13px; color: #6b7280; margin-bottom: 14px; }
.modal-textarea { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; resize: vertical; box-sizing: border-box; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px; }
.btn-primary { padding: 9px 20px; background: #2563eb; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 500; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.form-box { margin-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.form-row { display: flex; align-items: center; gap: 10px; }
.form-row label { font-size: 13px; color: #374151; white-space: nowrap; min-width: 90px; }
.form-row select { padding: 5px 8px; border: 1px solid #d1d5db; border-radius: 5px; font-size: 13px; }
.form-row input[type=range] { flex: 1; }
textarea { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; resize: vertical; box-sizing: border-box; }

.plan-status { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; font-size: 13px; color: #6b7280; }
.plan-submitted { color: #f59e0b; } .plan-approved { color: #10b981; } .plan-rejected { color: #ef4444; }
.plan-date { font-size: 12px; }
.plan-content { background: #f9fafb; border-radius: 6px; padding: 12px; font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
.feedback { margin-top: 10px; font-size: 13px; color: #1d4ed8; background: #eff6ff; padding: 10px 12px; border-radius: 6px; }

.update-list { display: flex; flex-direction: column; gap: 12px; }
.update-item { border: 1px solid #e5e7eb; border-radius: 7px; padding: 12px; }
.update-head { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; font-size: 13px; }
.update-type-progress { color: #7c3aed; font-weight: 600; }
.update-type-completion { color: #059669; font-weight: 600; }
.update-pct { background: #e0e7ff; color: #3730a3; border-radius: 4px; padding: 1px 6px; font-size: 12px; font-weight: 600; }
.update-date { color: #9ca3af; margin-left: auto; }
.update-content { font-size: 13px; color: #374151; line-height: 1.5; white-space: pre-wrap; }
</style>
