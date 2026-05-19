<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

interface Member { id: string; name: string; role: string | null; userRole: string; }
interface OverviewRow {
  id: string;
  taskId: string;
  taskTitle: string;
  taskStatus: string;
  taskDeadline: string | null;
  subTaskIndex: number;
  subTaskTitle: string;
  subTaskDescription: string | null;
  priority: string | null;
  status: string;
  workerStatus: string;
  approvedMemberId: string | null;
  approvedMemberName: string;
  approvedAt: string | null;
  memo: string | null;
  updatedAt: string;
}
interface TaskGroup {
  taskId: string;
  taskTitle: string;
  taskStatus: string;
  taskDeadline: string | null;
  rows: OverviewRow[];
}

const memberRole  = ref<string>(localStorage.getItem("smaas_member_role") ?? "");
const myMemberId  = ref<string>(localStorage.getItem("smaas_member_id") ?? "");
const isManager   = computed(() => memberRole.value === "manager");

const members      = ref<Member[]>([]);
const rows         = ref<OverviewRow[]>([]);
const filterMember = ref<string>("all"); // manager 전용 필터: "all" | member id
const filterStatus = ref<string>("all");
const loading      = ref(false);
const loadError    = ref<string>("");

// ── expand/collapse 상태 — computed 외부에서 관리해야 reactive하게 동작 ──
// computed 내부 객체를 직접 mutate하면 Vue가 변화를 추적하지 못함
const expandedMap = ref<Record<string, boolean>>({});
function isExpanded(taskId: string): boolean {
  return expandedMap.value[taskId] ?? true; // 기본: 펼침
}
function toggleGroup(taskId: string) {
  // 새 객체로 교체해야 Vue가 변화를 감지함
  expandedMap.value = { ...expandedMap.value, [taskId]: !isExpanded(taskId) };
}

const WORKER_STATUS_LABEL: Record<string, string> = {
  pending_acceptance: "수락 대기",
  accepted:           "수락됨",
  rejected:           "반려됨",
  in_progress:        "진행 중",
  done:               "완료 보고됨",
};
const WORKER_STATUS_COLOR: Record<string, string> = {
  pending_acceptance: "#f59e0b",
  accepted:           "#3b82f6",
  rejected:           "#ef4444",
  in_progress:        "#8b5cf6",
  done:               "#10b981",
};
const PRIORITY_COLOR: Record<string, string> = {
  high: "#ef4444", medium: "#f59e0b", low: "#6b7280",
};
const TASK_STATUS_COLOR: Record<string, string> = {
  planning:    "#6b7280",
  in_progress: "#3b82f6",
  review:      "#8b5cf6",
  done:        "#10b981",
  cancelled:   "#ef4444",
};

const STATUS_TABS = [
  { key: "all",                label: "전체" },
  { key: "pending_acceptance", label: "수락 대기" },
  { key: "accepted",           label: "수락됨" },
  { key: "in_progress",        label: "진행 중" },
  { key: "done",               label: "완료" },
  { key: "rejected",           label: "반려됨" },
];

async function loadMembers() {
  try {
    const res = await fetch("/api/members");
    if (!res.ok) return;
    const data = await res.json();
    members.value = Array.isArray(data) ? data : [];
  } catch { /* ignore */ }
}

async function loadOverview() {
  loading.value = true;
  loadError.value = "";
  try {
    // worker: 항상 자신의 id로 필터
    // manager: filterMember가 "all"이면 전체, 특정 id면 해당 멤버만
    let url = "/api/assignments/overview";
    if (!isManager.value) {
      if (myMemberId.value) {
        url += `?assignee_id=${myMemberId.value}`;
      }
    } else if (filterMember.value === "me") {
      url += `?assignee_id=${myMemberId.value}`;
    } else if (filterMember.value !== "all") {
      url += `?assignee_id=${filterMember.value}`;
    }

    const res = await fetch(url);

    // ── res.ok 미체크 시: FastAPI의 {"detail":"..."} 객체가 rows에 들어가
    //    for...of 루프에서 TypeError가 발생해 computed가 throw → blank page
    if (!res.ok) {
      loadError.value = `API 오류 (${res.status}): ${res.statusText}`;
      rows.value = [];
      return;
    }

    const data = await res.json();
    // 배열인지 반드시 확인 — 비배열이면 computed의 for...of가 throw해 blank page 발생
    rows.value = Array.isArray(data) ? data : [];
  } catch (e) {
    loadError.value = `네트워크 오류: ${String(e)}`;
    rows.value = [];
  } finally {
    loading.value = false;
  }
}

// 상태 탭 필터 + task 기준 그룹핑
const taskGroups = computed<TaskGroup[]>(() => {
  const filtered = filterStatus.value === "all"
    ? rows.value
    : rows.value.filter(r => r.workerStatus === filterStatus.value);

  const map = new Map<string, TaskGroup>();
  for (const r of filtered) {
    if (!map.has(r.taskId)) {
      map.set(r.taskId, {
        taskId:       r.taskId,
        taskTitle:    r.taskTitle,
        taskStatus:   r.taskStatus,
        taskDeadline: r.taskDeadline,
        rows:         [],
      });
    }
    map.get(r.taskId)!.rows.push(r);
  }
  for (const g of map.values()) {
    g.rows.sort((a, b) => a.subTaskIndex - b.subTaskIndex);
  }
  return Array.from(map.values());
});

// manager의 담당자 필터 변경 → 재로딩
watch(filterMember, loadOverview);

onMounted(async () => {
  // filterMember는 manager 전용 — worker는 onMounted에서 건드리지 않음
  // (worker URL 필터는 loadOverview 내에서 isManager/myMemberId로 처리)
  await loadMembers();
  await loadOverview();
});
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h1>업무 현황</h1>
        <p class="subtitle">{{ isManager ? "전체 담당자 업무 현황" : "내 배정 업무 목록" }}</p>
      </div>

      <!-- 관리자: 담당자 필터 -->
      <div v-if="isManager" class="filter-area">
        <label>담당자 필터</label>
        <select v-model="filterMember">
          <option value="all">전체</option>
          <option value="me">나 ({{ members.find(m => m.id === myMemberId)?.name ?? '' }})</option>
          <option
            v-for="m in members.filter(m => m.userRole !== 'manager')"
            :key="m.id"
            :value="m.id"
          >{{ m.name }}</option>
        </select>
      </div>

      <!-- Worker: 현재 사용자 표시 -->
      <div v-else-if="myMemberId" class="filter-area">
        <label>현재 사용자</label>
        <span class="current-user-chip">{{ members.find(m => m.id === myMemberId)?.name ?? myMemberId }}</span>
      </div>
    </div>

    <!-- 상태 탭 -->
    <div class="tabs">
      <button
        v-for="tab in STATUS_TABS"
        :key="tab.key"
        :class="['tab', { active: filterStatus === tab.key }]"
        @click="filterStatus = tab.key"
      >
        {{ tab.label }}
        <span class="tab-cnt" v-if="tab.key !== 'all'">
          {{ rows.filter(r => r.workerStatus === tab.key).length }}
        </span>
      </button>
    </div>

    <!-- 로딩 -->
    <div v-if="loading" class="loading">불러오는 중…</div>

    <!-- 에러 -->
    <div v-else-if="loadError" class="error-state">
      <div class="error-icon">⚠</div>
      <div>{{ loadError }}</div>
      <button class="retry-btn" @click="loadOverview">다시 시도</button>
    </div>

    <!-- 빈 상태 -->
    <div v-else-if="taskGroups.length === 0" class="empty-state">
      {{ rows.length === 0 ? "배정된 업무가 없습니다." : "해당 조건의 업무가 없습니다." }}
    </div>

    <!-- Task 그룹 목록 -->
    <div v-else class="group-list">
      <div v-for="group in taskGroups" :key="group.taskId" class="task-group">
        <!-- 그룹 헤더 -->
        <div class="group-header" @click="toggleGroup(group.taskId)">
          <div class="group-header-left">
            <span class="chevron">{{ isExpanded(group.taskId) ? "▼" : "▶" }}</span>
            <span class="group-title">{{ group.taskTitle }}</span>
            <span
              class="task-status-badge"
              :style="{ background: (TASK_STATUS_COLOR[group.taskStatus] ?? '#6b7280') + '20', color: TASK_STATUS_COLOR[group.taskStatus] ?? '#6b7280' }"
            >{{ group.taskStatus }}</span>
          </div>
          <div class="group-header-right">
            <span v-if="group.taskDeadline" class="deadline">마감 {{ group.taskDeadline }}</span>
            <span class="sub-count">{{ group.rows.length }}개 서브태스크</span>
          </div>
        </div>

        <!-- 서브태스크 목록 -->
        <div v-if="isExpanded(group.taskId)" class="subtask-list">
          <div
            v-for="r in group.rows"
            :key="r.id"
            class="subtask-row"
            @click="router.push(`/my-tasks/${r.id}`)"
          >
            <div class="subtask-index">#{{ r.subTaskIndex + 1 }}</div>
            <div class="subtask-body">
              <div class="subtask-title">{{ r.subTaskTitle }}</div>
              <div class="subtask-desc" v-if="r.subTaskDescription">{{ r.subTaskDescription }}</div>
            </div>
            <div class="subtask-meta">
              <span
                class="priority-badge"
                :style="{ background: (PRIORITY_COLOR[r.priority ?? 'low']) + '20', color: PRIORITY_COLOR[r.priority ?? 'low'] }"
              >{{ r.priority ?? "—" }}</span>
              <span
                class="status-badge"
                :style="{ background: WORKER_STATUS_COLOR[r.workerStatus] + '20', color: WORKER_STATUS_COLOR[r.workerStatus] }"
              >{{ WORKER_STATUS_LABEL[r.workerStatus] ?? r.workerStatus }}</span>
              <span v-if="isManager" class="assignee-chip">{{ r.approvedMemberName }}</span>
            </div>
            <span class="arrow">→</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 960px; margin: 0 auto; padding: 32px 24px; }

.page-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 24px; gap: 16px;
}
h1 { font-size: 22px; font-weight: 700; margin: 0 0 4px; }
.subtitle { font-size: 13px; color: #6b7280; margin: 0; }

.filter-area { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.filter-area label { font-size: 13px; color: #6b7280; white-space: nowrap; }
.filter-area select {
  padding: 6px 10px; border: 1px solid #d1d5db; border-radius: 6px;
  font-size: 13px; min-width: 160px;
}
.current-user-chip {
  padding: 5px 12px; border-radius: 20px;
  background: #ede9fe; color: #6d28d9;
  font-size: 13px; font-weight: 600; white-space: nowrap;
}

.tabs {
  display: flex; gap: 4px; margin-bottom: 20px;
  background: #f3f4f6; border-radius: 8px; padding: 4px; flex-wrap: wrap;
}
.tab {
  flex: 1; min-width: 72px; padding: 7px 6px; border: none; border-radius: 6px;
  background: transparent; cursor: pointer; font-size: 12px; color: #6b7280;
  display: flex; align-items: center; justify-content: center; gap: 4px;
}
.tab.active { background: #fff; color: #1f2937; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
.tab-cnt { background: #e5e7eb; border-radius: 10px; padding: 1px 5px; font-size: 11px; }

.loading { text-align: center; padding: 60px; color: #9ca3af; }
.empty-state { text-align: center; padding: 60px; color: #9ca3af; font-size: 15px; }

.error-state {
  text-align: center; padding: 60px; color: #ef4444; font-size: 14px;
  display: flex; flex-direction: column; align-items: center; gap: 12px;
}
.error-icon { font-size: 32px; }
.retry-btn {
  padding: 6px 18px; border: 1px solid #ef4444; border-radius: 6px;
  background: #fff; color: #ef4444; cursor: pointer; font-size: 13px;
}
.retry-btn:hover { background: #fef2f2; }

.group-list { display: flex; flex-direction: column; gap: 16px; }

.task-group {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden;
}

.group-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; cursor: pointer; background: #f9fafb;
  border-bottom: 1px solid #e5e7eb; gap: 12px;
  transition: background .1s;
}
.group-header:hover { background: #f3f4f6; }

.group-header-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.chevron { font-size: 11px; color: #9ca3af; flex-shrink: 0; }
.group-title { font-size: 15px; font-weight: 700; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.task-status-badge {
  padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; flex-shrink: 0;
}
.group-header-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.deadline { font-size: 12px; color: #ef4444; white-space: nowrap; }
.sub-count { font-size: 12px; color: #9ca3af; white-space: nowrap; }

.subtask-list { display: flex; flex-direction: column; }

.subtask-row {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 18px; border-bottom: 1px solid #f3f4f6; cursor: pointer;
  transition: background .1s;
}
.subtask-row:last-child { border-bottom: none; }
.subtask-row:hover { background: #f9fafb; }

.subtask-index {
  font-size: 12px; color: #9ca3af; font-weight: 600;
  min-width: 28px; flex-shrink: 0;
}
.subtask-body { flex: 1; min-width: 0; }
.subtask-title { font-size: 14px; font-weight: 600; color: #111827; }
.subtask-desc {
  font-size: 12px; color: #6b7280; margin-top: 2px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 400px;
}
.subtask-meta { display: flex; align-items: center; gap: 6px; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }

.priority-badge, .status-badge {
  display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; white-space: nowrap;
}
.assignee-chip {
  padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;
  background: #ede9fe; color: #6d28d9; white-space: nowrap;
}
.arrow { font-size: 13px; color: #9ca3af; flex-shrink: 0; }
</style>
