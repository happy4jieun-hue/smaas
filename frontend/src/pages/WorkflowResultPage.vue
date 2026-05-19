<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getTask } from "../api/tasks";
import { getWorkflowByTaskId } from "../api/workflows";
import AnalysisSection from "../components/AnalysisSection.vue";
import ErrorSection from "../components/ErrorSection.vue";
import MatchSection from "../components/MatchSection.vue";
import PlanSection from "../components/PlanSection.vue";
import StatusBadge from "../components/StatusBadge.vue";
import ValidationSection from "../components/ValidationSection.vue";
import type { Task, WorkflowRecord } from "../types";

const TERMINAL = new Set(["completed", "failed"]);
const POLL_MS = 3000;

const route = useRoute();
const router = useRouter();
const taskId = route.params.taskId as string;

const task = ref<Task | null>(null);
const workflow = ref<WorkflowRecord | null>(null);
const fetchError = ref<string | null>(null);
let timer: ReturnType<typeof setTimeout> | null = null;

async function fetchWorkflow() {
  try {
    workflow.value = await getWorkflowByTaskId(taskId);
    fetchError.value = null;
    if (!TERMINAL.has(workflow.value.status)) {
      timer = setTimeout(fetchWorkflow, POLL_MS);
    }
  } catch (err) {
    fetchError.value = err instanceof Error ? err.message : "조회 실패";
    timer = setTimeout(fetchWorkflow, POLL_MS);
  }
}

onMounted(() => {
  getTask(taskId).then(t => { task.value = t; }).catch(() => {});
  fetchWorkflow();
});
onUnmounted(() => { if (timer) clearTimeout(timer); });
</script>

<template>
  <div class="wrapper">
    <button class="back" @click="router.push('/')">← Task 목록</button>
    <!-- <h1 class="title">Workflow 결과</h1> -->
    <p v-if="task" class="task-title-sub">{{ task.title }}</p>

    <!-- <div class="meta-row">
      <span class="meta-label">Task ID</span>
      <code class="code">{{ taskId }}</code>
    </div> -->

    <div v-if="fetchError && !workflow" class="error-banner">
      {{ fetchError }} — 재시도 중...
    </div>

    <div v-if="!workflow && !fetchError" class="loading">
      <div class="spinner"></div>
      워크플로우 조회 중...
    </div>

    <template v-if="workflow">
      <div class="status-row">
        <StatusBadge :status="workflow.status" />
        <span v-if="!TERMINAL.has(workflow.status)" class="polling">
          폴링 중 ({{ POLL_MS / 1000 }}s마다 갱신)
        </span>
        <span class="updated">
          갱신: {{ new Date(workflow.updatedAt).toLocaleString("ko-KR") }}
        </span>
      </div>

      <div class="sections">
        <AnalysisSection
          v-if="workflow.context.steps.analyzed"
          :data="workflow.context.steps.analyzed"
        />
        <PlanSection
          v-if="workflow.context.steps.planned"
          :data="workflow.context.steps.planned"
        />
        <MatchSection
          v-if="workflow.context.steps.matched"
          :data="workflow.context.steps.matched"
          :taskId="taskId"
        />
        <ValidationSection
          v-if="workflow.context.steps.validated"
          :data="workflow.context.steps.validated"
        />

        <div v-if="workflow.context.steps.notified" class="section-notify">
          <h3 class="notify-title">알림 (Notifier)</h3>
          <div class="notify-row">
            <span :class="['badge', workflow.context.steps.notified.success ? 'pass' : 'fail']">
              {{ workflow.context.steps.notified.success ? "✓ 발송됨" : "✗ 실패" }}
            </span>
            <span class="channels">
              {{ workflow.context.steps.notified.channels.join(", ") }}
            </span>
          </div>
        </div>

        <ErrorSection
          v-if="workflow.context.errors.length > 0"
          :errors="workflow.context.errors"
        />

        <div
          v-if="!workflow.context.steps.analyzed && !TERMINAL.has(workflow.status)"
          class="pending-hint"
        >
          에이전트 실행 중입니다...
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.wrapper {
  max-width: 760px;
  margin: 32px auto;
  padding: 0 24px;
  font-family: "Segoe UI", sans-serif;
}
.back {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  margin-bottom: 20px;
}
.title {
  font-size: 22px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 4px;
}
.task-title-sub {
  font-size: 22px;
  color: #374151;
  margin: 0 0 16px;
  font-weight: 700;
}
.meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.meta-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
}
.code {
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  color: #374151;
}
.status-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.polling {
  font-size: 12px;
  color: #9ca3af;
}
.updated {
  font-size: 12px;
  color: #9ca3af;
  margin-left: auto;
}
.sections {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.error-banner {
  background: #fee2e2;
  color: #991b1b;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 16px;
}
.loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #6b7280;
  font-size: 14px;
  margin-top: 40px;
}
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.section-notify {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 16px 20px;
}
.notify-title {
  font-size: 14px;
  font-weight: 700;
  color: #1e40af;
  margin: 0 0 12px;
}
.notify-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.badge {
  padding: 3px 10px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 700;
}
.badge.pass { background: #dcfce7; color: #166534; }
.badge.fail { background: #fee2e2; color: #991b1b; }
.channels { font-size: 13px; color: #374151; }
.pending-hint {
  text-align: center;
  color: #9ca3af;
  font-size: 13px;
  padding: 20px;
}
</style>
