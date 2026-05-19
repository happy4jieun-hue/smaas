<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

const router    = useRouter();
const managerId = localStorage.getItem("smaas_member_id") ?? "";

// ─── Types ───────────────────────────────────────────────────────────────────
interface PlanItem {
  planId: string; assignmentId: string; taskId: string; taskTitle: string;
  subTaskTitle: string; priority: string | null; memberId: string;
  memberName: string; content: string; status: string;
  feedback: string | null; submittedAt: string; reviewedAt: string | null;
}
interface AssignmentRow {
  id: string; taskId: string; taskTitle: string; subTaskTitle: string;
  subTaskDescription: string | null; priority: string | null;
  workerStatus: string; status: string; approvedMemberId: string | null;
  approvedMemberName: string; approvedByName: string;
  approvedAt: string | null; memo: string | null; updatedAt: string;
}
interface UpdateRow {
  id: string; memberName: string; content: string;
  progressPercent: number; updateType: string; createdAt: string;
}
interface RejectedItem {
  id: string; taskId: string; taskTitle: string; subTaskTitle: string;
  subTaskDescription: string | null; priority: string | null;
  rejectionReason: string | null; rejectedAt: string | null;
  approvedMemberId: string | null; approvedMemberName: string;
  reassignmentCount: number;
  suggestedRole: string | null; suggestedReason: string | null;
}
interface Member { id: string; name: string; }

// ─── Tabs ─────────────────────────────────────────────────────────────────
const TABS = [
  { key: "all",         label: "전체" },
  { key: "plans",       label: "계획 승인" },
  { key: "in_progress", label: "진행 점검" },
  { key: "done",        label: "완료 검토" },
  { key: "rejected",    label: "반려 재배정" },
];
const activeTab = ref("all");

// ─── Data ──────────────────────────────────────────────────────────────────
const plans      = ref<PlanItem[]>([]);
const inProgress = ref<AssignmentRow[]>([]);
const doneItems  = ref<AssignmentRow[]>([]);
const rejected   = ref<RejectedItem[]>([]);
const members    = ref<Member[]>([]);
const loading    = ref(false);
const errMsg     = ref("");

// ─── Progress section ──────────────────────────────────────────────────────
const expanded    = ref<Set<string>>(new Set());
const updateCache = ref<Record<string, UpdateRow[]>>({});
const completing  = ref<string | null>(null);

// ─── Plan modal ───────────────────────────────────────────────────────────
const planModal    = ref<PlanItem | null>(null);
const planAction   = ref<"approve" | "reject" | null>(null);
const planFeedback = ref("");
const savingPlan   = ref<string | null>(null);
const planErr      = ref("");

// ─── Reassign modal ───────────────────────────────────────────────────────
const reassignModal    = ref<RejectedItem | null>(null);
const selectedMemberId = ref("");
const reassignMemo     = ref("");
const savingReassign   = ref<string | null>(null);
const reassignErr      = ref("");

// ─── Color maps ───────────────────────────────────────────────────────────
const PRIORITY_COLOR: Record<string, string> = {
  high: "#ef4444", medium: "#f59e0b", low: "#6b7280",
};

// ─── Computed: what to show per tab ──────────────────────────────────────
const visiblePlans      = computed(() => (activeTab.value === "all" || activeTab.value === "plans")      ? plans.value      : []);
const visibleInProgress = computed(() => (activeTab.value === "all" || activeTab.value === "in_progress") ? inProgress.value : []);
const visibleDone       = computed(() => (activeTab.value === "all" || activeTab.value === "done")        ? doneItems.value  : []);
const visibleRejected   = computed(() => (activeTab.value === "all" || activeTab.value === "rejected")    ? rejected.value   : []);

function tabCount(key: string) {
  if (key === "plans")       return plans.value.length;
  if (key === "in_progress") return inProgress.value.length;
  if (key === "done")        return doneItems.value.length;
  if (key === "rejected")    return rejected.value.length;
  if (key === "all")         return plans.value.length + inProgress.value.length + doneItems.value.length + rejected.value.length;
  return 0;
}

// ─── Load ─────────────────────────────────────────────────────────────────
async function loadAll() {
  loading.value = true; errMsg.value = "";
  try {
    const [pRes, ipRes, dRes, rRes, mRes] = await Promise.all([
      fetch("/api/admin/plans"),
      fetch("/api/admin/assignments?worker_status=in_progress"),
      fetch("/api/admin/assignments?worker_status=done"),
      fetch("/api/admin/rejected"),
      fetch("/api/members"),
    ]);
    plans.value      = await pRes.json();
    inProgress.value = await ipRes.json();
    doneItems.value  = await dRes.json();
    rejected.value   = await rRes.json();
    members.value    = await mRes.json();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function loadSection(tab: string) {
  if (tab === "all") { await loadAll(); return; }
  loading.value = true; errMsg.value = "";
  try {
    if (tab === "plans") {
      plans.value = await (await fetch("/api/admin/plans")).json();
    } else if (tab === "in_progress") {
      inProgress.value = await (await fetch("/api/admin/assignments?worker_status=in_progress")).json();
    } else if (tab === "done") {
      doneItems.value = await (await fetch("/api/admin/assignments?worker_status=done")).json();
    } else if (tab === "rejected") {
      const [rRes, mRes] = await Promise.all([fetch("/api/admin/rejected"), fetch("/api/members")]);
      rejected.value = await rRes.json();
      members.value  = await mRes.json();
    }
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    loading.value = false;
  }
}

// ─── Plan actions ─────────────────────────────────────────────────────────
function openPlanModal(plan: PlanItem, act: "approve" | "reject") {
  planModal.value    = plan;
  planAction.value   = act;
  planFeedback.value = plan.feedback ?? "";
  planErr.value      = "";
}
function closePlanModal() { planModal.value = null; planAction.value = null; planFeedback.value = ""; }

async function submitPlanAction() {
  if (!planModal.value || !planAction.value) return;
  savingPlan.value = planModal.value.planId;
  planErr.value = "";
  try {
    const body: Record<string, unknown> = {
      status: planAction.value === "approve" ? "approved" : "rejected",
    };
    if (planFeedback.value.trim()) body.feedback = planFeedback.value.trim();
    const res = await fetch(`/api/work-plans/${planModal.value.planId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    closePlanModal();
    plans.value = await (await fetch("/api/admin/plans")).json();
  } catch (e: any) {
    planErr.value = e.message;
  } finally {
    savingPlan.value = null;
  }
}

// ─── Progress actions ─────────────────────────────────────────────────────
async function toggleExpand(id: string) {
  const next = new Set(expanded.value);
  if (next.has(id)) { next.delete(id); expanded.value = next; return; }
  next.add(id); expanded.value = next;
  if (!updateCache.value[id]) {
    const res = await fetch(`/api/admin/assignments/${id}/updates`);
    updateCache.value = { ...updateCache.value, [id]: await res.json() };
  }
}

async function complete(id: string) {
  completing.value = id; errMsg.value = "";
  try {
    const url = `/api/admin/assignments/${id}/complete` + (managerId ? `?manager_id=${managerId}` : "");
    const res = await fetch(url, { method: "PATCH" });
    if (!res.ok) throw new Error(await res.text());
    doneItems.value = await (await fetch("/api/admin/assignments?worker_status=done")).json();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    completing.value = null;
  }
}

// ─── Rejected actions ─────────────────────────────────────────────────────
function memberName(id: string) { return members.value.find(m => m.id === id)?.name ?? id; }

function openReassignModal(item: RejectedItem) {
  reassignModal.value    = item;
  selectedMemberId.value = item.approvedMemberId || "";
  reassignMemo.value     = "";
  reassignErr.value      = "";
}
function closeReassignModal() { reassignModal.value = null; selectedMemberId.value = ""; reassignMemo.value = ""; }

async function submitReassign() {
  if (!reassignModal.value || !selectedMemberId.value) return;
  savingReassign.value = reassignModal.value.id;
  reassignErr.value = "";
  try {
    const res = await fetch(
      `/api/admin/assignments/${reassignModal.value.id}/reassign?manager_id=${managerId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ newMemberId: selectedMemberId.value, memo: reassignMemo.value || null }),
      }
    );
    if (!res.ok) throw new Error(await res.text());
    closeReassignModal();
    const [rRes, mRes] = await Promise.all([fetch("/api/admin/rejected"), fetch("/api/members")]);
    rejected.value = await rRes.json();
    members.value  = await mRes.json();
  } catch (e: any) {
    reassignErr.value = e.message;
  } finally {
    savingReassign.value = null;
  }
}

watch(activeTab, (tab) => loadSection(tab));
onMounted(loadAll);
</script>

<template>
  <div class="page">
    <!-- 헤더 -->
    <div class="page-header">
      <div>
        <h1>검토함</h1>
        <p class="subtitle">관리자 검토·조치가 필요한 항목을 모아봅니다</p>
      </div>
      <button class="btn-refresh" @click="loadSection(activeTab)">새로고침</button>
    </div>

    <!-- 탭 -->
    <div class="tabs">
      <button
        v-for="t in TABS"
        :key="t.key"
        :class="['tab', { active: activeTab === t.key }]"
        @click="activeTab = t.key"
      >
        {{ t.label }}
        <span v-if="tabCount(t.key) > 0" class="tab-cnt">{{ tabCount(t.key) }}</span>
      </button>
    </div>

    <div v-if="errMsg" class="err">{{ errMsg }}</div>
    <div v-if="loading" class="loading">로딩 중…</div>

    <div v-else-if="tabCount('all') === 0" class="empty">
      검토할 항목이 없습니다.
    </div>

    <div v-else class="content">

      <!-- ── 계획 승인 섹션 ────────────────────────────────────────── -->
      <template v-if="visiblePlans.length > 0">
        <div v-if="activeTab === 'all'" class="section-header">
          <span class="section-title">계획 승인</span>
          <span class="section-cnt">{{ visiblePlans.length }}건</span>
          <button class="section-link" @click="activeTab = 'plans'">전체 보기 →</button>
        </div>
        <div class="card-list">
          <div v-for="p in visiblePlans" :key="p.planId" class="plan-card">
            <div class="card-head">
              <div class="card-titles">
                <div class="task-link" @click="router.push(`/tasks/${p.taskId}/assignments`)">📋 {{ p.taskTitle }}</div>
                <div class="subtask-title">{{ p.subTaskTitle }}</div>
              </div>
              <div class="card-badges">
                <span v-if="p.priority" class="p-badge" :style="{ background: PRIORITY_COLOR[p.priority] + '20', color: PRIORITY_COLOR[p.priority] }">{{ p.priority }}</span>
                <span class="member-chip">👤 {{ p.memberName }}</span>
                <span class="date-chip">{{ p.submittedAt.slice(0, 10) }} 제출</span>
              </div>
            </div>
            <div class="plan-content">{{ p.content }}</div>
            <div v-if="p.feedback" class="old-feedback">이전 피드백: {{ p.feedback }}</div>
            <div class="card-actions">
              <button class="btn-approve" :disabled="savingPlan === p.planId" @click="openPlanModal(p, 'approve')">✓ 승인</button>
              <button class="btn-reject"  :disabled="savingPlan === p.planId" @click="openPlanModal(p, 'reject')">✕ 반려</button>
            </div>
          </div>
        </div>
      </template>
      <div v-else-if="activeTab === 'plans'" class="empty">검토 대기 중인 업무 계획이 없습니다.</div>

      <!-- ── 진행 점검 섹션 ────────────────────────────────────────── -->
      <template v-if="visibleInProgress.length > 0">
        <div v-if="activeTab === 'all'" class="section-header">
          <span class="section-title">진행 점검</span>
          <span class="section-cnt">{{ visibleInProgress.length }}건</span>
          <button class="section-link" @click="activeTab = 'in_progress'">전체 보기 →</button>
        </div>
        <div class="card-list">
          <div v-for="a in visibleInProgress" :key="a.id" class="assign-card">
            <div class="card-head">
              <div class="card-info">
                <div class="task-link" @click="router.push(`/tasks/${a.taskId}/assignments`)">📋 {{ a.taskTitle }}</div>
                <div class="subtask-title">{{ a.subTaskTitle }}</div>
                <div v-if="a.subTaskDescription" class="subtask-desc">{{ a.subTaskDescription }}</div>
              </div>
              <div class="card-badges">
                <span v-if="a.priority" class="p-badge" :style="{ background: PRIORITY_COLOR[a.priority] + '20', color: PRIORITY_COLOR[a.priority] }">{{ a.priority }}</span>
                <span class="member-chip">👤 {{ a.approvedMemberName || "—" }}</span>
                <span v-if="a.approvedAt" class="date-chip">{{ a.approvedAt.slice(0, 10) }} 배정</span>
              </div>
            </div>
            <div v-if="a.memo" class="memo">📝 {{ a.memo }}</div>
            <div class="expand-row">
              <button class="btn-expand" @click="toggleExpand(a.id)">
                {{ expanded.has(a.id) ? "▲ 보고 이력 닫기" : "▼ 보고 이력 보기" }}
              </button>
            </div>
            <div v-if="expanded.has(a.id)" class="updates">
              <div v-if="!updateCache[a.id]?.length" class="no-updates">보고 내역이 없습니다.</div>
              <div v-else v-for="u in updateCache[a.id]" :key="u.id" class="update-item">
                <div class="update-head">
                  <span :class="'type-' + u.updateType">{{ u.updateType === "completion" ? "✅ 완료 보고" : "📊 진행 보고" }}</span>
                  <span class="pct-badge">{{ u.progressPercent }}%</span>
                  <span class="update-member">{{ u.memberName }}</span>
                  <span class="update-date">{{ u.createdAt.slice(0, 10) }}</span>
                </div>
                <div class="update-content">{{ u.content }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-else-if="activeTab === 'in_progress'" class="empty">진행 중인 업무가 없습니다.</div>

      <!-- ── 완료 검토 섹션 ────────────────────────────────────────── -->
      <template v-if="visibleDone.length > 0">
        <div v-if="activeTab === 'all'" class="section-header">
          <span class="section-title">완료 검토</span>
          <span class="section-cnt">{{ visibleDone.length }}건</span>
          <button class="section-link" @click="activeTab = 'done'">전체 보기 →</button>
        </div>
        <div class="card-list">
          <div v-for="a in visibleDone" :key="a.id" class="assign-card done-card">
            <div class="card-head">
              <div class="card-info">
                <div class="task-link" @click="router.push(`/tasks/${a.taskId}/assignments`)">📋 {{ a.taskTitle }}</div>
                <div class="subtask-title">{{ a.subTaskTitle }}</div>
                <div v-if="a.subTaskDescription" class="subtask-desc">{{ a.subTaskDescription }}</div>
              </div>
              <div class="card-badges">
                <span v-if="a.priority" class="p-badge" :style="{ background: PRIORITY_COLOR[a.priority] + '20', color: PRIORITY_COLOR[a.priority] }">{{ a.priority }}</span>
                <span class="member-chip">👤 {{ a.approvedMemberName || "—" }}</span>
                <span v-if="a.approvedAt" class="date-chip">{{ a.approvedAt.slice(0, 10) }} 배정</span>
              </div>
            </div>
            <div v-if="a.memo" class="memo">📝 {{ a.memo }}</div>
            <div class="expand-row">
              <button class="btn-expand" @click="toggleExpand(a.id)">
                {{ expanded.has(a.id) ? "▲ 보고 이력 닫기" : "▼ 보고 이력 보기" }}
              </button>
              <button class="btn-complete" :disabled="completing === a.id" @click="complete(a.id)">
                {{ completing === a.id ? "처리 중…" : "✓ 완료 처리" }}
              </button>
            </div>
            <div v-if="expanded.has(a.id)" class="updates">
              <div v-if="!updateCache[a.id]?.length" class="no-updates">보고 내역이 없습니다.</div>
              <div v-else v-for="u in updateCache[a.id]" :key="u.id" class="update-item">
                <div class="update-head">
                  <span :class="'type-' + u.updateType">{{ u.updateType === "completion" ? "✅ 완료 보고" : "📊 진행 보고" }}</span>
                  <span class="pct-badge">{{ u.progressPercent }}%</span>
                  <span class="update-member">{{ u.memberName }}</span>
                  <span class="update-date">{{ u.createdAt.slice(0, 10) }}</span>
                </div>
                <div class="update-content">{{ u.content }}</div>
              </div>
            </div>
          </div>
        </div>
      </template>
      <div v-else-if="activeTab === 'done'" class="empty">완료 검토 대기 업무가 없습니다.</div>

      <!-- ── 반려 재배정 섹션 ──────────────────────────────────────── -->
      <template v-if="visibleRejected.length > 0">
        <div v-if="activeTab === 'all'" class="section-header">
          <span class="section-title">반려 재배정</span>
          <span class="section-cnt">{{ visibleRejected.length }}건</span>
          <button class="section-link" @click="activeTab = 'rejected'">전체 보기 →</button>
        </div>
        <div class="card-list">
          <div v-for="item in visibleRejected" :key="item.id" class="reject-card">
            <div class="card-head">
              <div class="card-info">
                <div class="task-link" @click="router.push(`/tasks/${item.taskId}/assignments`)">📋 {{ item.taskTitle }}</div>
                <div class="subtask-title">{{ item.subTaskTitle }}</div>
                <div v-if="item.subTaskDescription" class="subtask-desc">{{ item.subTaskDescription }}</div>
              </div>
              <div class="card-badges">
                <span v-if="item.priority" class="p-badge" :style="{ background: PRIORITY_COLOR[item.priority] + '20', color: PRIORITY_COLOR[item.priority] }">{{ item.priority }}</span>
                <span class="member-chip">👤 {{ item.approvedMemberName || "—" }}</span>
                <span v-if="item.reassignmentCount > 0" class="reassign-cnt">재배정 {{ item.reassignmentCount }}회</span>
              </div>
            </div>
            <div class="rejection-box">
              <span class="rejection-label">반려 사유</span>
              {{ item.rejectionReason || "—" }}
              <span v-if="item.rejectedAt" class="rejected-date">{{ item.rejectedAt.slice(0, 10) }}</span>
            </div>
            <div v-if="item.suggestedRole" class="ai-result">
              <span class="ai-label">AI 추천 역할</span>
              <span class="role-badge-sm">{{ item.suggestedRole }}</span>
              <span v-if="item.suggestedReason" class="ai-reason">— {{ item.suggestedReason }}</span>
            </div>
            <div class="card-actions">
              <button class="btn-reassign" @click="openReassignModal(item)">재배정 →</button>
            </div>
          </div>
        </div>
      </template>
      <div v-else-if="activeTab === 'rejected'" class="empty">반려된 업무가 없습니다.</div>

    </div><!-- /content -->

    <!-- ── 계획 승인/반려 모달 ─────────────────────────────────────── -->
    <div v-if="planModal" class="modal-overlay" @click.self="closePlanModal">
      <div class="modal">
        <h2>{{ planAction === "approve" ? "계획 승인" : "계획 반려" }}</h2>
        <div class="modal-info">
          <b>{{ planModal.memberName }}</b>의 <b>{{ planModal.subTaskTitle }}</b> 계획을
          {{ planAction === "approve" ? "승인" : "반려" }}합니다.
        </div>
        <div class="modal-field">
          <label>{{ planAction === "approve" ? "코멘트 (선택)" : "반려 사유 (선택)" }}</label>
          <textarea
            v-model="planFeedback" rows="3"
            :placeholder="planAction === 'reject' ? '반려 사유를 입력하면 worker에게 전달됩니다.' : '승인 코멘트를 남길 수 있습니다.'"
          />
        </div>
        <div v-if="planErr" class="err-inline">{{ planErr }}</div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="closePlanModal">취소</button>
          <button
            :class="planAction === 'approve' ? 'btn-approve' : 'btn-reject'"
            :disabled="!!savingPlan"
            @click="submitPlanAction"
          >
            {{ savingPlan ? "처리 중…" : (planAction === "approve" ? "승인 확정" : "반려 확정") }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── 재배정 모달 ─────────────────────────────────────────────── -->
    <div v-if="reassignModal" class="modal-overlay" @click.self="closeReassignModal">
      <div class="modal">
        <h2>재배정</h2>
        <div class="modal-info"><b>{{ reassignModal.subTaskTitle }}</b> 업무를 누구에게 배정하시겠습니까?</div>
        <div class="modal-field">
          <label>담당자 선택</label>
          <select v-model="selectedMemberId">
            <option value="">— 선택 —</option>
            <option v-for="m in members" :key="m.id" :value="m.id">
              {{ m.name }}{{ m.id === reassignModal.approvedMemberId ? " (기존 담당자)" : "" }}{{ aiResult[reassignModal.id]?.recommendedId === m.id ? " ⭐ AI 추천" : "" }}
            </option>
          </select>
        </div>
        <div class="modal-field">
          <label>메모 (선택)</label>
          <textarea v-model="reassignMemo" rows="2" placeholder="재배정 사유나 지시사항을 입력하세요." />
        </div>
        <div v-if="reassignErr" class="err-inline">{{ reassignErr }}</div>
        <div class="modal-actions">
          <button class="btn-cancel" @click="closeReassignModal">취소</button>
          <button class="btn-reassign-confirm" :disabled="!!savingReassign || !selectedMemberId" @click="submitReassign">
            {{ savingReassign ? "처리 중…" : "재배정 확정" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 900px; margin: 0 auto; padding: 32px 24px; }

.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; gap: 16px; }
h1 { font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.subtitle { font-size: 13px; color: #6b7280; margin: 0; }
.btn-refresh { padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; flex-shrink: 0; }

/* ── Tabs ── */
.tabs { display: flex; gap: 0; border-bottom: 2px solid #e5e7eb; margin-bottom: 28px; }
.tab {
  padding: 10px 18px; border: none; border-bottom: 2px solid transparent; margin-bottom: -2px;
  background: transparent; cursor: pointer; font-size: 14px; color: #6b7280;
  font-weight: 500; white-space: nowrap; display: flex; align-items: center; gap: 6px;
  transition: color .15s;
}
.tab.active { color: #2563eb; border-bottom-color: #2563eb; font-weight: 700; }
.tab:hover:not(.active) { color: #374151; }
.tab-cnt {
  background: #fee2e2; color: #b91c1c; border-radius: 10px;
  padding: 1px 6px; font-size: 11px; font-weight: 700;
}

.loading { text-align: center; padding: 60px; color: #9ca3af; }
.empty   { text-align: center; padding: 60px; color: #9ca3af; font-size: 15px; }
.err { background: #fef2f2; color: #b91c1c; border-radius: 6px; padding: 8px 12px; font-size: 13px; margin-bottom: 16px; }

/* ── Section headers (전체 탭 전용) ── */
.section-header {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 0 10px; margin-top: 16px; margin-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}
.section-header:first-child { margin-top: 0; }
.section-title { font-size: 15px; font-weight: 700; color: #111827; }
.section-cnt { font-size: 13px; color: #6b7280; }
.section-link { margin-left: auto; background: none; border: none; color: #2563eb; cursor: pointer; font-size: 13px; padding: 0; }

/* ── Card list ── */
.card-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 8px; }

/* ── Shared card head ── */
.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 12px; }
.card-titles, .card-info { flex: 1; }
.task-link { font-size: 12px; color: #2563eb; cursor: pointer; margin-bottom: 4px; }
.task-link:hover { text-decoration: underline; }
.subtask-title { font-size: 15px; font-weight: 600; color: #111827; }
.subtask-desc { font-size: 13px; color: #6b7280; margin-top: 3px; }
.card-badges { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; flex-shrink: 0; }
.p-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.member-chip { font-size: 12px; background: #f3f4f6; color: #374151; padding: 3px 8px; border-radius: 20px; }
.date-chip { font-size: 12px; color: #9ca3af; }
.reassign-cnt { font-size: 11px; background: #fef3c7; color: #92400e; padding: 2px 7px; border-radius: 4px; }

/* ── Plan card ── */
.plan-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; }
.plan-content { background: #f9fafb; border-radius: 6px; padding: 12px; font-size: 14px; line-height: 1.7; white-space: pre-wrap; color: #374151; margin-bottom: 12px; }
.old-feedback { font-size: 13px; color: #92400e; background: #fffbeb; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; }
.card-actions { display: flex; gap: 10px; }
.btn-approve { padding: 8px 18px; background: #10b981; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 13px; font-weight: 600; }
.btn-approve:hover:not(:disabled) { background: #059669; }
.btn-approve:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-reject { padding: 8px 18px; background: #fff; color: #ef4444; border: 1px solid #ef4444; border-radius: 7px; cursor: pointer; font-size: 13px; font-weight: 600; }
.btn-reject:hover:not(:disabled) { background: #fef2f2; }
.btn-reject:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── Assignment card ── */
.assign-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; }
.done-card { border-color: #a7f3d0; }
.memo { font-size: 13px; color: #92400e; background: #fffbeb; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; }
.expand-row { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
.btn-expand { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 13px; padding: 0; }
.btn-expand:hover { color: #374151; }
.btn-complete { margin-left: auto; padding: 7px 18px; background: #10b981; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 13px; font-weight: 600; }
.btn-complete:hover:not(:disabled) { background: #059669; }
.btn-complete:disabled { opacity: 0.5; cursor: not-allowed; }
.updates { margin-top: 12px; border-top: 1px solid #f3f4f6; padding-top: 12px; display: flex; flex-direction: column; gap: 10px; }
.no-updates { font-size: 13px; color: #9ca3af; text-align: center; padding: 10px 0; }
.update-item { border: 1px solid #e5e7eb; border-radius: 7px; padding: 10px 12px; }
.update-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 12px; }
.type-progress { color: #7c3aed; font-weight: 600; font-size: 13px; }
.type-completion { color: #059669; font-weight: 600; font-size: 13px; }
.pct-badge { background: #e0e7ff; color: #3730a3; padding: 1px 6px; border-radius: 4px; font-weight: 600; }
.update-member { color: #374151; font-weight: 500; }
.update-date { color: #9ca3af; margin-left: auto; }
.update-content { font-size: 13px; color: #374151; line-height: 1.5; white-space: pre-wrap; }

/* ── Reject card ── */
.reject-card { background: #fff; border: 1px solid #fca5a5; border-radius: 10px; padding: 18px; }
.rejection-box { background: #fef2f2; border-radius: 6px; padding: 10px 12px; font-size: 13px; color: #7f1d1d; margin-bottom: 10px; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.rejection-label { font-weight: 700; color: #ef4444; flex-shrink: 0; }
.rejected-date { font-size: 11px; color: #9ca3af; margin-left: auto; }
.ai-result { background: #f0fdf4; border-radius: 6px; padding: 10px 12px; font-size: 13px; margin-bottom: 10px; }
.ai-label { font-weight: 700; color: #059669; margin-right: 6px; }
.role-badge-sm { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; background: #dbeafe; color: #1d4ed8; }
.ai-reason { font-size: 12px; color: #6b7280; }
.btn-reassign { padding: 7px 18px; background: #2563eb; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 13px; font-weight: 600; }
.btn-reassign:disabled { opacity: 0.5; cursor: not-allowed; }

/* ── 모달 ── */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 460px; max-width: 95vw; }
.modal h2 { font-size: 18px; font-weight: 700; margin: 0 0 14px; }
.modal-info { font-size: 14px; color: #4b5563; margin-bottom: 16px; line-height: 1.5; }
.modal-field { margin-bottom: 14px; }
.modal-field label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.modal-field textarea, .modal-field select { width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; box-sizing: border-box; }
.modal-field textarea { resize: vertical; }
.err-inline { background: #fef2f2; color: #b91c1c; border-radius: 6px; padding: 8px 12px; font-size: 13px; margin-bottom: 10px; }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 16px; }
.btn-cancel { padding: 8px 18px; border: 1px solid #d1d5db; border-radius: 7px; background: #fff; cursor: pointer; font-size: 14px; }
.btn-reassign-confirm { padding: 8px 18px; background: #2563eb; color: #fff; border: none; border-radius: 7px; cursor: pointer; font-size: 14px; font-weight: 600; }
.btn-reassign-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
