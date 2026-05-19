<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { approveAllAssignments, getAssignments, patchAssignment } from "../api/assignments";
import { getMembers } from "../api/members";
import type { AssignmentStatus, MemberRecord, SubTaskAssignmentRecord } from "../types";

const route  = useRoute();
const router = useRouter();
const taskId = route.params.taskId as string;

const assignments = ref<SubTaskAssignmentRecord[]>([]);
const members     = ref<MemberRecord[]>([]);
const loading     = ref(true);
const error       = ref<string | null>(null);
const savingId    = ref<string | null>(null);
const approveAllLoading = ref(false);

// 각 행의 편집 상태
const editState = ref<Record<string, { selectedMemberId: string; memo: string }>>({});

// ── 역할 메타데이터 ──────────────────────────────────────────────────────────
const ROLE_META: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  planner:  { label: "기획",    color: "#6d28d9", bg: "#ede9fe", icon: "📋" },
  designer: { label: "디자인",  color: "#be185d", bg: "#fce7f3", icon: "🎨" },
  frontend: { label: "프론트",  color: "#1d4ed8", bg: "#dbeafe", icon: "🖥️" },
  backend:  { label: "백엔드",  color: "#b45309", bg: "#fef3c7", icon: "⚙️" },
  qa:       { label: "QA/테스트", color: "#065f46", bg: "#d1fae5", icon: "✅" },
};

function roleMeta(role?: string) {
  return role ? (ROLE_META[role] ?? { label: role, color: "#374151", bg: "#f3f4f6", icon: "👤" })
              : { label: "미정", color: "#9ca3af", bg: "#f9fafb", icon: "?" };
}

// ── 멤버 정렬: suggestedRole과 일치하는 멤버를 상단에 ─────────────────────────
function sortedMembers(suggestedRole?: string): MemberRecord[] {
  if (!suggestedRole) return members.value;
  const roleKey = suggestedRole.toLowerCase();
  const matched   = members.value.filter(m => (m.role ?? "").toLowerCase().includes(roleKey));
  const unmatched = members.value.filter(m => !(m.role ?? "").toLowerCase().includes(roleKey));
  return [...matched, ...unmatched];
}

function isRoleMatch(member: MemberRecord, suggestedRole?: string): boolean {
  if (!suggestedRole) return false;
  return (member.role ?? "").toLowerCase().includes(suggestedRole.toLowerCase());
}

// ── 일괄 승인 가능 수 ─────────────────────────────────────────────────────────
const readyToApproveCount = computed(() =>
  assignments.value.filter(
    a => a.status === "pending" && editState.value[a.id]?.selectedMemberId
  ).length
);

async function load() {
  try {
    [assignments.value, members.value] = await Promise.all([
      getAssignments(taskId),
      getMembers(),
    ]);
    for (const a of assignments.value) {
      editState.value[a.id] = {
        selectedMemberId: a.approvedMemberId ?? "",
        memo: a.memo ?? "",
      };
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "조회 실패";
  } finally {
    loading.value = false;
  }
}

function memberName(id?: string) {
  if (!id) return "—";
  return members.value.find(m => m.id === id)?.name ?? id;
}

const STATUS_LABEL: Record<AssignmentStatus, string> = {
  pending:  "대기",
  approved: "승인",
  changed:  "변경",
  rejected: "반려",
};
const STATUS_COLOR: Record<AssignmentStatus, string> = {
  pending:  "#fef9c3",
  approved: "#dcfce7",
  changed:  "#dbeafe",
  rejected: "#fee2e2",
};
const STATUS_TEXT: Record<AssignmentStatus, string> = {
  pending:  "#854d0e",
  approved: "#166534",
  changed:  "#1e40af",
  rejected: "#991b1b",
};

async function save(a: SubTaskAssignmentRecord, status: AssignmentStatus) {
  const state = editState.value[a.id];
  savingId.value = a.id;
  try {
    const updated = await patchAssignment(a.id, {
      approvedMemberId: state.selectedMemberId || undefined,
      status,
      memo: state.memo || undefined,
    });
    assignments.value = assignments.value.map(x => x.id === a.id ? updated : x);
    editState.value[a.id] = {
      selectedMemberId: updated.approvedMemberId ?? "",
      memo: updated.memo ?? "",
    };
  } catch (e) {
    error.value = e instanceof Error ? e.message : "저장 실패";
  } finally {
    savingId.value = null;
  }
}

async function approveAll() {
  if (readyToApproveCount.value === 0) {
    alert("담당자가 선택된 항목이 없습니다. 각 서브태스크에 담당자를 먼저 선택해 주세요.");
    return;
  }
  if (!confirm(`담당자가 선택된 ${readyToApproveCount.value}건을 일괄 승인하시겠습니까?`)) return;

  // 선택된 항목을 먼저 저장 후 일괄 승인
  approveAllLoading.value = true;
  try {
    // 선택된 멤버가 있는 pending 항목들을 개별 승인
    const pendingWithMember = assignments.value.filter(
      a => a.status === "pending" && editState.value[a.id]?.selectedMemberId
    );
    for (const a of pendingWithMember) {
      const state = editState.value[a.id];
      const updated = await patchAssignment(a.id, {
        approvedMemberId: state.selectedMemberId,
        status: "approved",
        memo: state.memo || undefined,
      });
      assignments.value = assignments.value.map(x => x.id === a.id ? updated : x);
    }
    alert(`${pendingWithMember.length}건이 승인되었습니다.`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "일괄 승인 실패";
  } finally {
    approveAllLoading.value = false;
  }
}

const PRIORITY_COLOR: Record<string, string> = { high: "#fee2e2", medium: "#fef9c3", low: "#dcfce7" };
const PRIORITY_TEXT: Record<string, string>  = { high: "#991b1b", medium: "#854d0e", low: "#166534" };

onMounted(load);
</script>

<template>
  <div class="wrapper">
    <button class="back" @click="router.push(`/workflows/${taskId}`)">← Workflow 결과</button>
    <div class="page-header">
      <div>
        <h1 class="title">담당자 배정</h1>
        <p class="subtitle">AI 추천 역할을 참고해 실제 담당자를 선택하세요</p>
      </div>
      <button
        class="btn-approve-all"
        :disabled="approveAllLoading || readyToApproveCount === 0"
        @click="approveAll"
      >
        {{ approveAllLoading ? "처리 중..." : `전체 승인 (${readyToApproveCount}건 준비됨)` }}
      </button>
    </div>

    <div v-if="error" class="error-box">{{ error }}<button class="dismiss" @click="error=null">✕</button></div>
    <div v-if="loading" class="empty">불러오는 중...</div>
    <div v-else-if="assignments.length === 0" class="empty">
      배정 데이터가 없습니다. Workflow가 Matcher 단계까지 완료됐는지 확인하세요.
    </div>

    <div v-else class="cards">
      <div v-for="a in assignments" :key="a.id" class="card">

        <!-- 카드 상단: 번호 + 제목 + 우선순위 + 상태 -->
        <div class="card-head">
          <div class="subtask-info">
            <span class="idx">{{ a.subTaskIndex + 1 }}</span>
            <span class="subtask-title">{{ a.subTaskTitle }}</span>
            <span
              v-if="a.priority"
              class="priority"
              :style="{ background: PRIORITY_COLOR[a.priority] ?? '#f3f4f6', color: PRIORITY_TEXT[a.priority] ?? '#374151' }"
            >{{ a.priority }}</span>
          </div>
          <span
            class="status-badge"
            :style="{ background: STATUS_COLOR[a.status], color: STATUS_TEXT[a.status] }"
          >{{ STATUS_LABEL[a.status] }}</span>
        </div>

        <p v-if="a.subTaskDescription" class="desc">{{ a.subTaskDescription }}</p>

        <!-- AI 추천 역할 -->
        <div class="role-row">
          <span class="role-label">AI 추천 역할</span>
          <span
            class="role-badge"
            :style="{ background: roleMeta(a.suggestedRole).bg, color: roleMeta(a.suggestedRole).color }"
          >
            {{ roleMeta(a.suggestedRole).icon }} {{ roleMeta(a.suggestedRole).label }}
          </span>
          <span v-if="a.suggestedReason" class="role-reason">— {{ a.suggestedReason }}</span>
        </div>

        <!-- 관리자 배정 UI -->
        <div class="action-row">
          <div class="select-wrap">
            <label class="field-label">담당자 선택</label>
            <select v-model="editState[a.id].selectedMemberId" class="select">
              <option value="">— 선택 —</option>
              <template v-for="m in sortedMembers(a.suggestedRole)" :key="m.id">
                <option :value="m.id">
                  {{ isRoleMatch(m, a.suggestedRole) ? "★ " : "" }}{{ m.name }}{{ m.role ? ` (${m.role})` : "" }}
                </option>
              </template>
            </select>
            <span v-if="editState[a.id]?.selectedMemberId" class="selected-hint">
              선택됨: <strong>{{ memberName(editState[a.id].selectedMemberId) }}</strong>
            </span>
          </div>
          <div class="memo-wrap">
            <label class="field-label">메모</label>
            <input v-model="editState[a.id].memo" class="memo-input" placeholder="배정 메모 (선택)" />
          </div>
        </div>

        <!-- 액션 버튼 -->
        <div class="btn-row">
          <button
            class="btn-action approve"
            :disabled="savingId === a.id || !editState[a.id]?.selectedMemberId"
            @click="save(a, 'approved')"
          >✓ 승인</button>
          <button
            class="btn-action change"
            :disabled="savingId === a.id || !editState[a.id]?.selectedMemberId"
            @click="save(a, 'changed')"
          >↔ 변경</button>
          <button
            class="btn-action reject"
            :disabled="savingId === a.id"
            @click="save(a, 'rejected')"
          >✕ 반려</button>
        </div>

        <!-- 최종 배정 결과 -->
        <div v-if="a.approvedMemberId" class="approved-result">
          최종 배정: <strong>{{ memberName(a.approvedMemberId) }}</strong>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.wrapper { max-width: 860px; margin: 32px auto; padding: 0 24px; font-family: "Segoe UI", sans-serif; }
.back { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 14px; padding: 0; margin-bottom: 16px; }
.page-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 24px; gap: 16px; }
.title { font-size: 22px; font-weight: 700; color: #111827; margin: 0 0 4px; }
.subtitle { font-size: 13px; color: #6b7280; margin: 0; }

.btn-approve-all { padding: 8px 16px; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; white-space: nowrap; flex-shrink: 0; margin-top: 4px; }
.btn-approve-all:hover:not(:disabled) { background: #1d4ed8; }
.btn-approve-all:disabled { opacity: 0.5; cursor: not-allowed; }

.cards { display: flex; flex-direction: column; gap: 16px; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 18px 20px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.subtask-info { display: flex; align-items: center; gap: 8px; flex: 1; }
.idx { width: 24px; height: 24px; border-radius: 50%; background: #2563eb; color: #fff; font-size: 12px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.subtask-title { font-size: 15px; font-weight: 600; color: #111827; }
.priority { padding: 2px 8px; border-radius: 99px; font-size: 11px; font-weight: 600; }
.status-badge { padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.desc { font-size: 13px; color: #6b7280; margin: 0 0 12px; line-height: 1.5; }

/* 역할 추천 행 */
.role-row { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.role-label { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; white-space: nowrap; }
.role-badge { display: inline-flex; align-items: center; gap: 4px; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; }
.role-reason { font-size: 12px; color: #6b7280; flex: 1; }

/* 배정 UI */
.field-label { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; }
.action-row { display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.select-wrap { display: flex; flex-direction: column; gap: 4px; flex: 0 0 240px; }
.memo-wrap { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 160px; }
.select { padding: 7px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; color: #111827; }
.memo-input { padding: 7px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; color: #111827; }
.selected-hint { font-size: 12px; color: #059669; margin-top: 2px; }

.btn-row { display: flex; gap: 8px; }
.btn-action { padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; }
.btn-action:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-action.approve { background: #dcfce7; color: #166534; }
.btn-action.approve:hover:not(:disabled) { background: #bbf7d0; }
.btn-action.change { background: #dbeafe; color: #1e40af; }
.btn-action.change:hover:not(:disabled) { background: #bfdbfe; }
.btn-action.reject { background: #fee2e2; color: #991b1b; }
.btn-action.reject:hover:not(:disabled) { background: #fecaca; }

.approved-result { margin-top: 10px; font-size: 13px; color: #374151; background: #f0fdf4; border-radius: 6px; padding: 8px 12px; }
.empty { text-align: center; color: #9ca3af; font-size: 14px; margin-top: 60px; }
.error-box { background: #fee2e2; color: #991b1b; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; display: flex; justify-content: space-between; }
.dismiss { background: none; border: none; color: #991b1b; cursor: pointer; font-size: 14px; }
</style>
