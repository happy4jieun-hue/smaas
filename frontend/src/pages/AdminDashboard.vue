<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

interface DashboardStats {
  totalTasks: number;
  pendingAssignments: number;
  pendingWorkPlans: number;
  unreadNotifications: number;
  tasksByStatus: Record<string, number>;
  recentTasks: { id: string; title: string; status: string; deadline: string | null; createdAt: string }[];
}

const stats = ref<DashboardStats | null>(null);
const loading = ref(true);

const STATUS_LABEL: Record<string, string> = {
  pending: "대기", running: "실행 중", completed: "완료", failed: "실패",
};
const STATUS_COLOR: Record<string, string> = {
  pending: "#f59e0b", running: "#3b82f6", completed: "#10b981", failed: "#ef4444",
};

async function load() {
  loading.value = true;
  try {
    const res = await fetch("/api/dashboard");
    stats.value = await res.json();
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header">
      <h1>관리자 대시보드</h1>
      <button class="btn-refresh" @click="load">새로고침</button>
    </div>

    <div v-if="loading" class="loading">로딩 중…</div>

    <template v-else-if="stats">
      <!-- 통계 카드 -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-num">{{ stats.totalTasks }}</div>
          <div class="stat-label">전체 업무</div>
        </div>
        <div class="stat-card warn" @click="router.push('/admin/assignments')">
          <div class="stat-num">{{ stats.pendingAssignments }}</div>
          <div class="stat-label">배정 검토 대기</div>
          <div class="stat-hint" v-if="stats.pendingAssignments > 0">클릭하여 검토</div>
        </div>
        <div class="stat-card info" @click="router.push('/admin/plans')">
          <div class="stat-num">{{ stats.pendingWorkPlans }}</div>
          <div class="stat-label">계획 승인 대기</div>
        </div>
        <div class="stat-card neutral">
          <div class="stat-num">{{ stats.unreadNotifications }}</div>
          <div class="stat-label">읽지 않은 알림</div>
        </div>
      </div>

      <!-- 상태별 현황 -->
      <div class="section">
        <h2>업무 상태 현황</h2>
        <div class="status-bar-wrap">
          <div
            v-for="(cnt, status) in stats.tasksByStatus"
            :key="status"
            class="status-bar-item"
          >
            <span class="status-dot" :style="{ background: STATUS_COLOR[status] ?? '#6b7280' }"></span>
            <span class="status-name">{{ STATUS_LABEL[status] ?? status }}</span>
            <span class="status-cnt">{{ cnt }}</span>
          </div>
        </div>
      </div>

      <!-- 최근 업무 -->
      <div class="section">
        <div class="section-head">
          <h2>최근 등록 업무</h2>
          <button class="btn-link" @click="router.push('/')">전체 보기 →</button>
        </div>
        <table class="table">
          <thead>
            <tr><th>제목</th><th>상태</th><th>마감일</th><th>등록일</th><th></th></tr>
          </thead>
          <tbody>
            <tr v-for="t in stats.recentTasks" :key="t.id">
              <td class="title-cell">{{ t.title }}</td>
              <td>
                <span class="badge" :style="{ background: STATUS_COLOR[t.status] ?? '#6b7280' }">
                  {{ STATUS_LABEL[t.status] ?? t.status }}
                </span>
              </td>
              <td>{{ t.deadline ?? "—" }}</td>
              <td>{{ t.createdAt.slice(0, 10) }}</td>
              <td>
                <button class="btn-sm" @click="router.push(`/tasks/${t.id}/assignments`)">배정 검토</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 빠른 이동 -->
      <div class="section">
        <h2>바로가기</h2>
        <div class="quick-links">
          <button class="quick-btn" @click="router.push('/tasks/new')">+ 업무 등록</button>
          <button class="quick-btn" @click="router.push('/members')">팀원 관리</button>
          <button class="quick-btn" @click="router.push('/')">업무 목록</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.page { max-width: 1000px; margin: 0 auto; padding: 32px 24px; }
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
h1 { font-size: 22px; font-weight: 700; margin: 0; }
h2 { font-size: 16px; font-weight: 600; margin: 0 0 14px; }
.btn-refresh { padding: 6px 14px; border: 1px solid #d1d5db; border-radius: 6px; background: #fff; cursor: pointer; font-size: 13px; }
.loading { text-align: center; padding: 60px; color: #9ca3af; }

.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }
.stat-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;
  padding: 20px; text-align: center; cursor: default;
}
.stat-card.warn { border-color: #fbbf24; background: #fffbeb; cursor: pointer; }
.stat-card.info { border-color: #60a5fa; background: #eff6ff; cursor: pointer; }
.stat-card.neutral { border-color: #d1d5db; }
.stat-num { font-size: 36px; font-weight: 800; color: #1f2937; }
.stat-label { font-size: 13px; color: #6b7280; margin-top: 4px; }
.stat-hint { font-size: 11px; color: #b45309; margin-top: 4px; }

.section { background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.section-head h2 { margin: 0; }
.btn-link { background: none; border: none; color: #2563eb; cursor: pointer; font-size: 13px; }

.status-bar-wrap { display: flex; flex-wrap: wrap; gap: 12px; }
.status-bar-item { display: flex; align-items: center; gap: 6px; font-size: 14px; }
.status-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.status-name { color: #374151; }
.status-cnt { font-weight: 700; color: #111827; }

.table { width: 100%; border-collapse: collapse; font-size: 14px; }
.table th { text-align: left; padding: 8px 12px; color: #6b7280; font-weight: 600; border-bottom: 1px solid #e5e7eb; }
.table td { padding: 10px 12px; border-bottom: 1px solid #f3f4f6; }
.title-cell { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; color: #fff; font-weight: 600; }
.btn-sm { padding: 4px 10px; border: 1px solid #d1d5db; border-radius: 5px; background: #fff; cursor: pointer; font-size: 12px; }
.btn-sm:hover { background: #f9fafb; }

.quick-links { display: flex; gap: 12px; }
.quick-btn { padding: 10px 20px; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; cursor: pointer; font-size: 14px; font-weight: 500; }
.quick-btn:hover { background: #f9fafb; border-color: #2563eb; color: #2563eb; }
</style>
