<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

interface AssignmentRow {
  id: string;
  taskId: string;
  taskTitle: string;
  subTaskTitle: string;
  subTaskDescription: string | null;
  priority: string | null;
  workerStatus: string;
  status: string;
  approvedMemberId: string | null;
  approvedMemberName: string;
  approvedByName: string;
  approvedAt: string | null;
  memo: string | null;
  updatedAt: string;
}
interface UpdateRow {
  id: string;
  memberName: string;
  content: string;
  progressPercent: number;
  updateType: string;
  createdAt: string;
}

// 탭: in_progress = 진행 점검, done = 완료 검토
const TABS = [
  { key: "in_progress", label: "진행 점검",  color: "#7c3aed" },
  { key: "done",        label: "완료 검토",  color: "#f59e0b" },
  { key: "completed",   label: "완료 처리됨", color: "#10b981" },
];

const activeTab   = ref("in_progress");
const assignments = ref<AssignmentRow[]>([]);
const loading     = ref(false);
const completing  = ref<string | null>(null);
const errMsg      = ref("");

// 확장된 행(보고 내용 표시)
const expanded    = ref<Set<string>>(new Set());
const updateCache = ref<Record<string, UpdateRow[]>>({});

const PRIORITY_COLOR: Record<string, string> = {
  high: "#ef4444", medium: "#f59e0b", low: "#6b7280",
};

async function load() {
  loading.value = true;
  errMsg.value  = "";
  assignments.value = [];
  try {
    const res = await fetch(`/api/admin/assignments?worker_status=${activeTab.value}`);
    assignments.value = await res.json();
  } finally {
    loading.value = false;
  }
}

async function toggleExpand(id: string) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id);
    return;
  }
  expanded.value.add(id);
  if (!updateCache.value[id]) {
    const res = await fetch(`/api/admin/assignments/${id}/updates`);
    updateCache.value[id] = await res.json();
  }
}

const managerId = localStorage.getItem("smaas_member_id") ?? "";

async function complete(id: string) {
  completing.value = id;
  errMsg.value = "";
  try {
    const url = `/api/admin/assignments/${id}/complete` + (managerId ? `?manager_id=${managerId}` : "");
    const res = await fetch(url, { method: "PATCH" });
    if (!res.ok) throw new Error(await res.text());
    await load();
  } catch (e: any) {
    errMsg.value = e.message;
  } finally {
    completing.value = null;
  }
}

watch(activeTab, load);
onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header">
      <button class="back-btn" @click="router.push('/admin')">← 대시보드</button>
      <h1>진행 점검 / 완료 검토</h1>
      <button class="btn-refresh" @click="load">새로고침</button>
    </div>

    <!-- 탭 -->
    <div class="tabs">
      <button
        v-for="t in TABS"
        :key="t.key"
        :class="['tab', { active: activeTab === t.key }]"
        :style="activeTab === t.key ? { borderColor: t.color, color: t.color } : {}"
        @click="activeTab = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <div v-if="errMsg" class="err">{{ errMsg }}</div>
    <div v-if="loading" class="loading">로딩 중…</div>

    <div v-else-if="assignments.length === 0" class="empty">
      {{ activeTab === "in_progress" ? "진행 중인 업무가 없습니다." :
         activeTab === "done" ? "완료 검토 대기 업무가 없습니다." : "완료 처리된 업무가 없습니다." }}
    </div>

    <div v-else class="list">
      <div v-for="a in assignments" :key="a.id" class="card">
        <!-- 카드 헤더 -->
        <div class="card-head">
          <div class="card-info">
            <div class="task-link" @click="router.push(`/tasks/${a.taskId}/assignments`)">
              📋 {{ a.taskTitle }}
            </div>
            <div class="subtask-title">{{ a.subTaskTitle }}</div>
            <div v-if="a.subTaskDescription" class="subtask-desc">{{ a.subTaskDescription }}</div>
          </div>
          <div class="card-badges">
            <span v-if="a.priority" class="p-badge" :style="{ background: PRIORITY_COLOR[a.priority] + '20', color: PRIORITY_COLOR[a.priority] }">
              {{ a.priority }}
            </span>
            <span class="member-chip">👤 {{ a.approvedMemberName || "—" }}</span>
            <span class="date-chip" v-if="a.approvedAt">{{ a.approvedAt.slice(0, 10) }} 배정</span>
          </div>
        </div>

        <!-- 메모 -->
        <div v-if="a.memo" class="memo">📝 {{ a.memo }}</div>

        <!-- 보고 이력 토글 -->
        <div class="expand-row">
          <button class="btn-expand" @click="toggleExpand(a.id)">
            {{ expanded.has(a.id) ? "▲ 보고 이력 닫기" : "▼ 보고 이력 보기" }}
          </button>

          <!-- 완료 처리 버튼 (done 상태만) -->
          <button
            v-if="activeTab === 'done'"
            class="btn-complete"
            :disabled="completing === a.id"
            @click="complete(a.id)"
          >
            {{ completing === a.id ? "처리 중…" : "✓ 완료 처리" }}
          </button>
        </div>

        <!-- 보고 이력 -->
        <div v-if="expanded.has(a.id)" class="updates">
          <div v-if="!updateCache[a.id] || updateCache[a.id].length === 0" class="no-updates">
            보고 내역이 없습니다.
          </div>
          <div v-else v-for="u in updateCache[a.id]" :key="u.id" class="update-item">
            <div class="update-head">
              <span :class="'type-' + u.updateType">
                {{ u.updateType === "completion" ? "✅ 완료 보고" : "📊 진행 보고" }}
              </span>
              <span class="pct-badge">{{ u.progressPercent }}%</span>
              <span class="update-member">{{ u.memberName }}</span>
              <span class="update-date">{{ u.createdAt.slice(0, 10) }}</span>
            </div>
            <div class="update-content">{{ u.content }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 900px; margin: 0 auto; padding: 32px 24px; }
.header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
h1 { font-size: 22px; font-weight: 700; margin: 0; flex: 1; }
.back-btn { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 13px; padding: 0; flex-shrink: 0; }
.btn-refresh { padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }
.loading, .empty { text-align: center; padding: 60px; color: #9ca3af; }
.err { background: #fef2f2; color: #b91c1c; border-radius: 6px; padding: 8px 12px; font-size: 13px; margin-bottom: 14px; }

.tabs { display: flex; gap: 0; border-bottom: 1px solid #e5e7eb; margin-bottom: 24px; }
.tab {
  padding: 10px 20px; border: none; border-bottom: 2px solid transparent;
  background: transparent; cursor: pointer; font-size: 14px; color: #6b7280;
  font-weight: 500; transition: all .15s;
}
.tab.active { font-weight: 700; }
.tab:hover:not(.active) { color: #374151; }

.list { display: flex; flex-direction: column; gap: 14px; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 18px; }

.card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.card-info { flex: 1; }
.task-link { font-size: 12px; color: #2563eb; cursor: pointer; margin-bottom: 4px; }
.task-link:hover { text-decoration: underline; }
.subtask-title { font-size: 15px; font-weight: 600; color: #111827; }
.subtask-desc { font-size: 13px; color: #6b7280; margin-top: 3px; }
.card-badges { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; flex-shrink: 0; }
.p-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.member-chip { font-size: 12px; background: #f3f4f6; padding: 3px 8px; border-radius: 20px; }
.date-chip { font-size: 12px; color: #9ca3af; }
.memo { font-size: 13px; color: #92400e; background: #fffbeb; padding: 8px 12px; border-radius: 6px; margin-bottom: 10px; }

.expand-row { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
.btn-expand { background: none; border: none; color: #6b7280; cursor: pointer; font-size: 13px; padding: 0; }
.btn-expand:hover { color: #374151; }
.btn-complete {
  margin-left: auto; padding: 7px 18px; background: #10b981; color: #fff;
  border: none; border-radius: 7px; cursor: pointer; font-size: 13px; font-weight: 600;
}
.btn-complete:hover:not(:disabled) { background: #059669; }
.btn-complete:disabled { opacity: 0.5; cursor: not-allowed; }

.updates { margin-top: 12px; border-top: 1px solid #f3f4f6; padding-top: 12px; display: flex; flex-direction: column; gap: 10px; }
.no-updates { font-size: 13px; color: #9ca3af; text-align: center; padding: 12px 0; }
.update-item { border: 1px solid #e5e7eb; border-radius: 7px; padding: 10px 12px; }
.update-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 12px; }
.type-progress { color: #7c3aed; font-weight: 600; font-size: 13px; }
.type-completion { color: #059669; font-weight: 600; font-size: 13px; }
.pct-badge { background: #e0e7ff; color: #3730a3; padding: 1px 6px; border-radius: 4px; font-weight: 600; }
.update-member { color: #374151; font-weight: 500; }
.update-date { color: #9ca3af; margin-left: auto; }
.update-content { font-size: 13px; color: #374151; line-height: 1.5; white-space: pre-wrap; }
</style>
