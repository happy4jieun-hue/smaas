<script setup lang="ts">
import { computed, onMounted, onUnmounted, provide, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

interface Member { id: string; name: string; userRole: string; }

const members    = ref<Member[]>([]);
const memberId   = ref<string>(localStorage.getItem("smaas_member_id") ?? "");
const memberRole = ref<string>(localStorage.getItem("smaas_member_role") ?? "");
const unreadCount = ref(0);

const currentMember = computed(() => members.value.find(m => m.id === memberId.value));
const isManager     = computed(() => memberRole.value === "manager");

// ── SSE 연결 관리 ────────────────────────────────────────────
// NotificationsPage가 inject 해서 count 변화 시 목록을 자동 새로고침한다
const refreshNotifTrigger = ref(0);
provide("refreshNotifTrigger", refreshNotifTrigger);

let _es: EventSource | null = null;
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let _reconnectDelay = 1_000; // ms — 재연결 시 지수 증가, 최대 30s

function connectSSE(id: string) {
  // 기존 연결 및 재연결 타이머 정리
  if (_es) { _es.close(); _es = null; }
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
  if (!id) return;

  _es = new EventSource(`/api/notifications/stream?member_id=${id}`);

  _es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (typeof data.count === "number" && data.count !== unreadCount.value) {
        unreadCount.value = data.count;
        refreshNotifTrigger.value++; // NotificationsPage 목록 새로고침 트리거
      }
    } catch { /* JSON 파싱 오류 무시 */ }
    _reconnectDelay = 1_000; // 정상 수신 → 딜레이 초기화
  };

  _es.onerror = () => {
    _es?.close();
    _es = null;
    // 지수 백오프: 1s → 2s → 4s → 8s → … → 30s 상한
    _reconnectTimer = setTimeout(() => {
      _reconnectDelay = Math.min(_reconnectDelay * 2, 30_000);
      connectSSE(memberId.value);
    }, _reconnectDelay);
  };
}

async function loadMembers() {
  try {
    const res = await fetch("/api/members");
    members.value = await res.json();
    const m = members.value.find(m => m.id === memberId.value);
    if (m) {
      memberRole.value = m.userRole;
      localStorage.setItem("smaas_member_role", m.userRole);
    }
  } catch { /* API 미동작 시 무시 */ }
}

async function fetchInitialCount() {
  // SSE 연결 전 gap을 메우는 1회성 HTTP 폴 — 마운트 직후 badge 즉시 표시용
  const id = memberId.value;
  if (!id) return;
  try {
    const res = await fetch(`/api/notifications/count?member_id=${id}`);
    if (res.ok) {
      const data = await res.json();
      unreadCount.value = data.count ?? 0;
    }
  } catch { /* 무시 */ }
}

function switchMember(id: string) {
  memberId.value = id;
  localStorage.setItem("smaas_member_id", id);
  const m = members.value.find(m => m.id === id);
  if (m) {
    memberRole.value = m.userRole;
    localStorage.setItem("smaas_member_role", m.userRole);
  }
  unreadCount.value = 0;
  _reconnectDelay = 1_000;
  connectSSE(id); // 사용자 변경 → SSE 재연결
  router.push(m?.userRole === "manager" ? "/admin" : "/my-tasks");
}

onMounted(async () => {
  await loadMembers();
  await fetchInitialCount(); // badge 즉시 표시
  connectSSE(memberId.value); // SSE 연결 (이후 실시간 갱신)
});

onUnmounted(() => {
  if (_es) { _es.close(); _es = null; }
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
});
</script>

<template>
  <div>
    <nav class="nav">
      <span class="brand" @click="router.push('/')">SMAAS</span>

      <div class="nav-links">
        <!-- 항상 표시 -->
        <button class="nav-btn" @click="router.push('/')">Task 목록</button>
        <button class="nav-btn primary" @click="router.push('/tasks/new')">+ 새 Task</button>
        <button class="nav-btn" @click="router.push('/members')">팀원 관리</button>

        <!-- 관리자 메뉴 -->
        <template v-if="isManager">
          <span class="divider">|</span>
          <button class="nav-btn role-btn manager" @click="router.push('/admin')">대시보드</button>
          <button class="nav-btn" @click="router.push('/my-tasks')">업무 현황</button>
          <button class="nav-btn" @click="router.push('/admin/review')">검토함</button>
          <button class="nav-btn notif-btn" @click="router.push('/admin/notifications')">
            🔔 알림<span v-if="unreadCount > 0" class="notif-dot">{{ unreadCount }}</span>
          </button>
        </template>

        <!-- worker 메뉴 -->
        <template v-else-if="memberId">
          <span class="divider">|</span>
          <button class="nav-btn role-btn worker" @click="router.push('/my-tasks')">업무 현황</button>
          <button class="nav-btn notif-btn" @click="router.push('/notifications')">
            🔔 알림<span v-if="unreadCount > 0" class="notif-dot">{{ unreadCount }}</span>
          </button>
        </template>
      </div>

      <!-- 사용자 전환 -->
      <div class="user-area">
        <template v-if="currentMember">
          <span class="user-chip" :class="memberRole">
            {{ currentMember.name }} · {{ memberRole === "manager" ? "관리자" : "Worker" }}
          </span>
        </template>
        <select
          class="member-switcher"
          :value="memberId"
          @change="switchMember(($event.target as HTMLSelectElement).value)"
        >
          <option value="">— 사용자 선택 —</option>
          <option v-for="m in members" :key="m.id" :value="m.id">
            {{ m.name }} ({{ m.userRole === "manager" ? "관리자" : "Worker" }})
          </option>
        </select>
      </div>
    </nav>

    <RouterView :key="memberId" />
  </div>
</template>

<style scoped>
.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 10;
  gap: 12px;
}
.brand {
  font-size: 18px;
  font-weight: 800;
  color: #2563eb;
  cursor: pointer;
  letter-spacing: -0.5px;
  flex-shrink: 0;
}
.nav-links { display: flex; align-items: center; gap: 6px; }
.divider { color: #d1d5db; font-size: 18px; margin: 0 2px; }

.nav-btn {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.nav-btn:hover { background: #f9fafb; }
.nav-btn.primary { background: #2563eb; color: #fff; border-color: #2563eb; }
.nav-btn.primary:hover { background: #1d4ed8; }
.nav-btn.role-btn.manager { border-color: #2563eb; color: #2563eb; background: #eff6ff; }
.nav-btn.role-btn.worker { border-color: #7c3aed; color: #7c3aed; background: #f5f3ff; }
.nav-btn.notif-btn { position: relative; }
.notif-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: 10px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  margin-left: 4px;
  vertical-align: middle;
}

.user-area { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.user-chip {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  white-space: nowrap;
}
.user-chip.manager { background: #dbeafe; color: #1d4ed8; }
.user-chip.worker  { background: #ede9fe; color: #6d28d9; }
.member-switcher {
  padding: 5px 8px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 12px;
  max-width: 160px;
}
</style>
