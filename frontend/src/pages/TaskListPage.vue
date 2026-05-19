<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { deleteTask, getTasks } from "../api/tasks";
import StatusBadge from "../components/StatusBadge.vue";
import type { Task } from "../types";

const router = useRouter();
const tasks = ref<Task[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const deletingId = ref<string | null>(null);
const deleteError = ref<string | null>(null);

async function load() {
  try {
    tasks.value = await getTasks();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "조회 실패";
  } finally {
    loading.value = false;
  }
}

async function handleDelete(task: Task, e: MouseEvent) {
  e.stopPropagation(); // 카드 클릭(워크플로우 이동) 방지
  deleteError.value = null;

  if (!confirm(`"${task.title}" Task를 삭제하시겠습니까?\n관련 워크플로우 데이터도 함께 삭제됩니다.`)) {
    return;
  }

  deletingId.value = task.id;
  try {
    await deleteTask(task.id);
    tasks.value = tasks.value.filter(t => t.id !== task.id);
  } catch (err) {
    deleteError.value = err instanceof Error ? err.message : "삭제 실패";
  } finally {
    deletingId.value = null;
  }
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

onMounted(load);
</script>

<template>
  <div class="wrapper">
    <div class="header">
      <h1 class="title">Task 목록</h1>
      <button class="btn-new" @click="router.push('/tasks/new')">+ 새 Task</button>
    </div>

    <div v-if="deleteError" class="error-box banner">
      삭제 실패: {{ deleteError }}
      <button class="dismiss" @click="deleteError = null">✕</button>
    </div>

    <div v-if="loading" class="empty">불러오는 중...</div>
    <div v-else-if="error" class="error-box">{{ error }}</div>
    <div v-else-if="tasks.length === 0" class="empty">
      아직 생성된 Task가 없습니다.<br />
      <button class="link-btn" @click="router.push('/tasks/new')">첫 번째 Task 만들기 →</button>
    </div>

    <div v-else class="list">
      <div
        v-for="task in tasks"
        :key="task.id"
        class="card"
        @click="router.push(`/workflows/${task.id}`)"
      >
        <div class="card-top">
          <span class="task-title">{{ task.title }}</span>
          <div class="card-actions" @click.stop>
            <StatusBadge :status="task.status" />
            <button
              class="btn-delete"
              :disabled="deletingId === task.id"
              @click="handleDelete(task, $event)"
            >
              {{ deletingId === task.id ? "삭제 중..." : "삭제" }}
            </button>
          </div>
        </div>
        <p class="task-desc">{{ task.description }}</p>
        <div class="card-meta">
          <span v-if="task.deadline" class="meta-item">마감: {{ task.deadline }}</span>
          <span class="meta-item">생성: {{ formatDate(task.createdAt) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrapper {
  max-width: 800px;
  margin: 40px auto;
  padding: 0 24px;
  font-family: "Segoe UI", sans-serif;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.title {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}
.btn-new {
  padding: 8px 16px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
.btn-new:hover { background: #1d4ed8; }
.list { display: flex; flex-direction: column; gap: 12px; }
.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px 20px;
  cursor: pointer;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.card:hover {
  border-color: #2563eb;
  box-shadow: 0 2px 8px rgba(37,99,235,0.1);
}
.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.task-title {
  font-size: 15px;
  font-weight: 600;
  color: #111827;
  flex: 1;
  margin-right: 12px;
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.btn-delete {
  padding: 4px 10px;
  font-size: 12px;
  color: #dc2626;
  background: #fff;
  border: 1px solid #fca5a5;
  border-radius: 5px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.12s;
}
.btn-delete:hover:not(:disabled) {
  background: #fee2e2;
}
.btn-delete:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.task-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 10px;
  line-height: 1.5;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.card-meta {
  display: flex;
  gap: 16px;
}
.meta-item {
  font-size: 12px;
  color: #9ca3af;
}
.empty {
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
  margin-top: 60px;
  line-height: 2;
}
.link-btn {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 14px;
  cursor: pointer;
  margin-top: 8px;
}
.error-box {
  background: #fee2e2;
  color: #991b1b;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
}
.banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.dismiss {
  background: none;
  border: none;
  color: #991b1b;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  line-height: 1;
}
</style>
