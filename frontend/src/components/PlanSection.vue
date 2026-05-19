<script setup lang="ts">
import type { PlanResult } from "../types";
defineProps<{ data: PlanResult }>();

const priorityColor: Record<string, string> = {
  high: "#fee2e2",
  medium: "#fef9c3",
  low: "#dcfce7",
};
const priorityText: Record<string, string> = {
  high: "#991b1b",
  medium: "#854d0e",
  low: "#166534",
};
</script>

<template>
  <div class="section">
    <h3 class="section-title">
      계획 (Planner)
      <span class="total-hours">총 {{ data.estimatedTotalHours }}h</span>
    </h3>
    <div class="tasks">
      <div v-for="(sub, i) in data.subTasks" :key="i" class="sub-task">
        <div class="sub-top">
          <span class="sub-num">{{ i + 1 }}</span>
          <span class="sub-title">{{ sub.title }}</span>
          <span
            class="priority"
            :style="{ background: priorityColor[sub.priority], color: priorityText[sub.priority] }"
          >{{ sub.priority }}</span>
        </div>
        <p class="sub-desc">{{ sub.description }}</p>
        <div v-if="sub.dependsOn.length > 0" class="depends">
          의존: {{ sub.dependsOn.join(", ") }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; }
.section-title { font-size: 14px; font-weight: 700; color: #1e40af; margin: 0 0 14px; display: flex; align-items: center; gap: 10px; }
.total-hours { font-size: 12px; color: #6b7280; font-weight: 400; }
.tasks { display: flex; flex-direction: column; gap: 10px; }
.sub-task { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 14px; }
.sub-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.sub-num { width: 22px; height: 22px; border-radius: 50%; background: #2563eb; color: #fff; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sub-title { font-size: 13px; font-weight: 600; color: #111827; flex: 1; }
.priority { padding: 2px 8px; border-radius: 99px; font-size: 11px; font-weight: 600; }
.sub-desc { font-size: 12px; color: #6b7280; margin: 0 0 6px; line-height: 1.5; }
.depends { font-size: 11px; color: #9ca3af; }
</style>
