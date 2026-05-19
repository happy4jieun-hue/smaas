<script setup lang="ts">
import { useRouter } from "vue-router";
import type { MatchResult, RolesSummary } from "../types";

const props = defineProps<{ data: MatchResult; taskId: string }>();
const router = useRouter();

const ROLE_META: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  planner:  { label: "기획",      color: "#6d28d9", bg: "#ede9fe", icon: "📋" },
  designer: { label: "디자인",    color: "#be185d", bg: "#fce7f3", icon: "🎨" },
  frontend: { label: "프론트",    color: "#1d4ed8", bg: "#dbeafe", icon: "🖥️" },
  backend:  { label: "백엔드",    color: "#b45309", bg: "#fef3c7", icon: "⚙️" },
  qa:       { label: "QA/테스트", color: "#065f46", bg: "#d1fae5", icon: "✅" },
};

function roleMeta(role?: string) {
  return role ? (ROLE_META[role] ?? { label: role, color: "#374151", bg: "#f3f4f6", icon: "👤" })
              : { label: "미정", color: "#9ca3af", bg: "#f9fafb", icon: "?" };
}

function summaryEntries(rs?: RolesSummary) {
  if (!rs) return [];
  return (Object.entries(rs) as [string, number][]).filter(([, v]) => v > 0);
}
</script>

<template>
  <div class="section">
    <div class="section-head">
      <h3 class="section-title">역할 추천 (Matcher)</h3>
      <button class="btn-review" @click="router.push(`/tasks/${taskId}/assignments`)">
        담당자 배정 →
      </button>
    </div>

    <!-- 역할 요약 -->
    <div v-if="data.rolesSummary && summaryEntries(data.rolesSummary).length > 0" class="summary-row">
      <span class="summary-label">필요 역할</span>
      <span
        v-for="[role, cnt] in summaryEntries(data.rolesSummary)"
        :key="role"
        class="summary-chip"
        :style="{ background: roleMeta(role).bg, color: roleMeta(role).color }"
      >
        {{ roleMeta(role).icon }} {{ roleMeta(role).label }} × {{ cnt }}
      </span>
    </div>

    <!-- 서브태스크별 역할 -->
    <div class="assignments">
      <div v-for="a in data.assignments" :key="a.subTaskIndex" class="asgn-card">
        <div class="asgn-top">
          <span class="idx">{{ a.subTaskIndex + 1 }}</span>
          <span class="asgn-title">{{ a.subTaskTitle }}</span>
          <span
            class="role-badge"
            :style="{ background: roleMeta(a.suggestedRole).bg, color: roleMeta(a.suggestedRole).color }"
          >
            {{ roleMeta(a.suggestedRole).icon }} {{ roleMeta(a.suggestedRole).label }}
          </span>
        </div>
        <p v-if="a.suggestedReason" class="reason">{{ a.suggestedReason }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.section { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px 20px; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.section-title { font-size: 14px; font-weight: 700; color: #1e40af; margin: 0; }
.btn-review { padding: 5px 12px; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-size: 12px; cursor: pointer; }
.btn-review:hover { background: #1d4ed8; }

.summary-row { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; padding: 8px 12px; background: #fff; border-radius: 8px; border: 1px solid #e5e7eb; }
.summary-label { font-size: 11px; font-weight: 700; color: #6b7280; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; margin-right: 4px; }
.summary-chip { padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap; }

.assignments { display: flex; flex-direction: column; gap: 8px; }
.asgn-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 14px; }
.asgn-top { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.idx { width: 22px; height: 22px; border-radius: 50%; background: #2563eb; color: #fff; font-size: 11px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.asgn-title { font-size: 13px; font-weight: 600; color: #111827; flex: 1; }
.role-badge { padding: 2px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; white-space: nowrap; flex-shrink: 0; }
.reason { font-size: 12px; color: #6b7280; margin: 6px 0 0 30px; line-height: 1.4; }
</style>
