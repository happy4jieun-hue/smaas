<script setup lang="ts">
import { inject, onMounted, ref, watch } from "vue";
import type { Ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

interface NotifItem {
  id: string;
  type: string;
  title: string;
  body: string;
  isRead: boolean;
  relatedTaskId: string | null;
  relatedAssignmentId: string | null;
  createdAt: string;
}

const memberId     = localStorage.getItem("smaas_member_id") ?? "";
const memberRole   = localStorage.getItem("smaas_member_role") ?? "";
const notifications = ref<NotifItem[]>([]);
const loading       = ref(false);
const markingAll    = ref(false);

const TYPE_LABEL: Record<string, string> = {
  task_assigned:       "업무 배정",
  plan_review:         "계획 검토 요청",
  plan_approved:       "계획 승인",
  plan_rejected:       "계획 반려",
  progress_submitted:  "진행 보고 수신",
  assignment_review:   "배정 검토 요청",
  worker_rejected:     "Worker 반려",
  task_registered:     "신규 업무 등록",
  completion_reviewed: "완료 확정",
  reassigned:          "업무 재배정",
};

const TYPE_COLOR: Record<string, string> = {
  task_assigned:       "#2563eb",
  plan_review:         "#f59e0b",
  plan_approved:       "#10b981",
  plan_rejected:       "#ef4444",
  progress_submitted:  "#7c3aed",
  assignment_review:   "#f59e0b",
  worker_rejected:     "#ef4444",
  task_registered:     "#2563eb",
  completion_reviewed: "#10b981",
  reassigned:          "#f59e0b",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  if (diff < 60_000)        return "방금";
  if (diff < 3_600_000)     return `${Math.floor(diff / 60_000)}분 전`;
  if (diff < 86_400_000)    return `${Math.floor(diff / 3_600_000)}시간 전`;
  if (diff < 604_800_000)   return `${Math.floor(diff / 86_400_000)}일 전`;
  return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
}

async function load() {
  if (!memberId) return;
  loading.value = true;
  try {
    const res = await fetch(`/api/notifications?member_id=${memberId}`);
    notifications.value = await res.json();
  } finally {
    loading.value = false;
  }
}

async function markRead(n: NotifItem) {
  if (n.isRead) {
    navigate(n);
    return;
  }
  await fetch(`/api/notifications/${n.id}/read`, { method: "PATCH" });
  n.isRead = true;
  navigate(n);
}

function navigate(n: NotifItem) {
  if (n.relatedAssignmentId && memberRole !== "manager") {
    router.push(`/my-tasks/${n.relatedAssignmentId}`);
  } else if (n.relatedTaskId) {
    router.push(`/tasks/${n.relatedTaskId}/assignments`);
  }
}

async function markAllRead() {
  if (!memberId) return;
  markingAll.value = true;
  try {
    await fetch(`/api/notifications/read-all?member_id=${memberId}`, { method: "POST" });
    notifications.value.forEach(n => (n.isRead = true));
  } finally {
    markingAll.value = false;
  }
}

const unreadCount = () => notifications.value.filter(n => !n.isRead).length;

// App.vue SSE 트리거 — count 변화 시 목록 자동 새로고침
const refreshTrigger = inject<Ref<number>>("refreshNotifTrigger", ref(0));
watch(refreshTrigger, () => { if (memberId) load(); });

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header">
      <button class="back-btn" @click="router.push(memberRole === 'manager' ? '/admin' : '/my-tasks')">
        ← {{ memberRole === "manager" ? "대시보드" : "내 업무" }}
      </button>
      <h1>알림</h1>
      <button
        v-if="unreadCount() > 0"
        class="btn-mark-all"
        :disabled="markingAll"
        @click="markAllRead"
      >
        {{ markingAll ? "처리 중…" : "모두 읽음 처리" }}
      </button>
    </div>

    <div v-if="!memberId" class="empty">사용자를 먼저 선택해 주세요.</div>
    <div v-else-if="loading" class="loading">로딩 중…</div>
    <div v-else-if="notifications.length === 0" class="empty">알림이 없습니다.</div>

    <div v-else class="notif-list">
      <div
        v-for="n in notifications"
        :key="n.id"
        :class="['notif-item', { unread: !n.isRead }]"
        @click="markRead(n)"
      >
        <div class="notif-left">
          <span
            class="type-badge"
            :style="{ background: (TYPE_COLOR[n.type] ?? '#6b7280') + '20', color: TYPE_COLOR[n.type] ?? '#6b7280' }"
          >
            {{ TYPE_LABEL[n.type] ?? n.type }}
          </span>
          <div class="notif-title">{{ n.title }}</div>
          <div class="notif-body">{{ n.body }}</div>
        </div>
        <div class="notif-right">
          <span class="notif-date">{{ formatDate(n.createdAt) }}</span>
          <span v-if="!n.isRead" class="unread-dot" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page { max-width: 720px; margin: 0 auto; padding: 32px 24px; }
.header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
h1 { font-size: 22px; font-weight: 700; margin: 0; flex: 1; }
.back-btn { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 13px; padding: 0; flex-shrink: 0; }
.btn-mark-all { padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; white-space: nowrap; }
.btn-mark-all:hover:not(:disabled) { background: #f9fafb; }
.btn-mark-all:disabled { opacity: 0.5; cursor: not-allowed; }
.loading, .empty { text-align: center; padding: 60px; color: #9ca3af; }

.notif-list { display: flex; flex-direction: column; gap: 8px; }
.notif-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: background .1s;
}
.notif-item:hover { background: #f9fafb; }
.notif-item.unread { border-color: #bfdbfe; background: #eff6ff; }
.notif-item.unread:hover { background: #dbeafe; }

.notif-left { flex: 1; }
.type-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-bottom: 6px; }
.notif-title { font-size: 14px; font-weight: 600; color: #111827; margin-bottom: 3px; }
.notif-body { font-size: 13px; color: #4b5563; line-height: 1.5; }

.notif-right { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0; }
.notif-date { font-size: 12px; color: #9ca3af; white-space: nowrap; }
.unread-dot { width: 8px; height: 8px; border-radius: 50%; background: #2563eb; }
</style>
