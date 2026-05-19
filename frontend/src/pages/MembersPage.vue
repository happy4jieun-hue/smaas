<script setup lang="ts">
import { onMounted, ref } from "vue";
import { createMember, deleteMember, getMembers, updateMember } from "../api/members";
import type { MemberInput, MemberRecord, MemberUpdate } from "../types";

const members = ref<MemberRecord[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// 모달 상태
const showModal = ref(false);
const editingId = ref<string | null>(null);
const saving = ref(false);
const form = ref<MemberInput>(emptyForm());
const deletingId = ref<string | null>(null);

function emptyForm(): MemberInput {
  return {
    name: "", email: "", team: "", role: "", grade: "",
    userRole: "worker",
    skills: [], preferred_stages: [], services: [],
    capacity: 100, current_load: 0,
    available_hours_today: 8, available_hours_tomorrow: 8,
    timezone: "Asia/Seoul",
  };
}

function parseTagInput(val: string): string[] {
  return val.split(",").map(s => s.trim()).filter(Boolean);
}

// skills/preferred_stages/services는 콤마 구분 문자열로 편집
const skillsInput = ref("");
const stagesInput = ref("");
const servicesInput = ref("");

async function load() {
  try { members.value = await getMembers(); }
  catch (e) { error.value = e instanceof Error ? e.message : "조회 실패"; }
  finally { loading.value = false; }
}

function openCreate() {
  editingId.value = null;
  form.value = emptyForm();
  skillsInput.value = "";
  stagesInput.value = "";
  servicesInput.value = "";
  showModal.value = true;
}

function openEdit(m: MemberRecord) {
  editingId.value = m.id;
  form.value = {
    name: m.name, email: m.email ?? "", team: m.team ?? "",
    role: m.role ?? "", grade: m.grade ?? "",
    userRole: m.userRole ?? "worker",
    skills: [...m.skills], preferred_stages: [...m.preferred_stages], services: [...m.services],
    capacity: m.capacity, current_load: m.current_load,
    available_hours_today: m.available_hours_today,
    available_hours_tomorrow: m.available_hours_tomorrow,
    timezone: m.timezone,
  };
  skillsInput.value = m.skills.join(", ");
  stagesInput.value = m.preferred_stages.join(", ");
  servicesInput.value = m.services.join(", ");
  showModal.value = true;
}

async function save() {
  form.value.skills = parseTagInput(skillsInput.value);
  form.value.preferred_stages = parseTagInput(stagesInput.value);
  form.value.services = parseTagInput(servicesInput.value);
  saving.value = true;
  try {
    if (editingId.value) {
      const updated = await updateMember(editingId.value, form.value as MemberUpdate);
      members.value = members.value.map(m => m.id === editingId.value ? updated : m);
    } else {
      const created = await createMember(form.value);
      members.value = [created, ...members.value];
    }
    showModal.value = false;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "저장 실패";
  } finally {
    saving.value = false;
  }
}

async function handleDelete(m: MemberRecord) {
  if (!confirm(`"${m.name}"을(를) 삭제하시겠습니까?`)) return;
  deletingId.value = m.id;
  try {
    await deleteMember(m.id);
    members.value = members.value.filter(x => x.id !== m.id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "삭제 실패";
  } finally {
    deletingId.value = null;
  }
}

onMounted(load);
</script>

<template>
  <div class="wrapper">
    <div class="header">
      <h1 class="title">팀원 관리</h1>
      <button class="btn-primary" @click="openCreate">+ 팀원 추가</button>
    </div>

    <div v-if="error" class="error-box">{{ error }}<button class="dismiss" @click="error=null">✕</button></div>
    <div v-if="loading" class="empty">불러오는 중...</div>
    <div v-else-if="members.length === 0" class="empty">등록된 팀원이 없습니다.</div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>이름</th><th>시스템 역할</th><th>직무 / 직급</th><th>팀</th>
          <th>스킬</th><th>capacity</th><th>부하</th><th>가용시간</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in members" :key="m.id">
          <td>
            <div class="name">{{ m.name }}</div>
            <div class="sub">{{ m.email }}</div>
          </td>
          <td>
            <span :class="['role-chip', m.userRole]">
              {{ m.userRole === "manager" ? "관리자" : "Worker" }}
            </span>
          </td>
          <td>
            <div>{{ m.role ?? "—" }}</div>
            <div class="sub">{{ m.grade ?? "" }}</div>
          </td>
          <td>{{ m.team ?? "—" }}</td>
          <td>
            <div class="tags">
              <span v-for="s in m.skills" :key="s" class="tag">{{ s }}</span>
            </div>
          </td>
          <td>
            <div class="bar-wrap">
              <div class="bar cap" :style="{ width: m.capacity + '%' }"></div>
              <span class="bar-label">{{ m.capacity }}%</span>
            </div>
          </td>
          <td>
            <div class="bar-wrap">
              <div class="bar load" :style="{ width: m.current_load + '%' }"></div>
              <span class="bar-label">{{ m.current_load }}%</span>
            </div>
          </td>
          <td class="hours">{{ m.available_hours_today }}h / {{ m.available_hours_tomorrow }}h</td>
          <td class="actions">
            <button class="btn-sm" @click="openEdit(m)">수정</button>
            <button class="btn-sm danger" :disabled="deletingId === m.id" @click="handleDelete(m)">
              {{ deletingId === m.id ? "..." : "삭제" }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- 모달 -->
    <div v-if="showModal" class="overlay" @click.self="showModal=false">
      <div class="modal">
        <h2 class="modal-title">{{ editingId ? "팀원 수정" : "팀원 추가" }}</h2>
        <div class="form-grid">
          <label>이름 *<input v-model="form.name" /></label>
          <label>이메일<input v-model="form.email" /></label>
          <label>팀<input v-model="form.team" /></label>
          <label>직무 역할<input v-model="form.role" placeholder="예: Backend Engineer" /></label>
          <label>직급<input v-model="form.grade" placeholder="예: Senior" /></label>
          <label>시스템 권한
            <select v-model="form.userRole">
              <option value="worker">Worker</option>
              <option value="manager">관리자 (Manager)</option>
            </select>
          </label>
          <label>Timezone<input v-model="form.timezone" /></label>
          <label class="full">스킬 (콤마 구분)<input v-model="skillsInput" placeholder="Python, FastAPI, SQL" /></label>
          <label class="full">선호 단계 (콤마 구분)<input v-model="stagesInput" placeholder="planning, development" /></label>
          <label class="full">담당 서비스 (콤마 구분)<input v-model="servicesInput" placeholder="auth, api-gateway" /></label>
          <label>Capacity (%)<input v-model.number="form.capacity" type="number" min="0" max="100" /></label>
          <label>현재 부하 (%)<input v-model.number="form.current_load" type="number" min="0" max="100" /></label>
          <label>가용시간 오늘(h)<input v-model.number="form.available_hours_today" type="number" min="0" step="0.5" /></label>
          <label>가용시간 내일(h)<input v-model.number="form.available_hours_tomorrow" type="number" min="0" step="0.5" /></label>
        </div>
        <div class="modal-footer">
          <button class="btn-outline" @click="showModal=false">취소</button>
          <button class="btn-primary" :disabled="saving || !form.name" @click="save">
            {{ saving ? "저장 중..." : "저장" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.wrapper { max-width: 1100px; margin: 40px auto; padding: 0 24px; font-family: "Segoe UI", sans-serif; }
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.title { font-size: 22px; font-weight: 700; color: #111827; margin: 0; }
.btn-primary { padding: 8px 16px; background: #2563eb; color: #fff; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { padding: 8px 16px; background: #fff; color: #374151; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; cursor: pointer; }
.table { width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }
th { background: #f9fafb; padding: 10px 12px; font-size: 12px; font-weight: 600; color: #6b7280; text-align: left; border-bottom: 1px solid #e5e7eb; }
td { padding: 12px; border-bottom: 1px solid #f3f4f6; vertical-align: middle; font-size: 13px; color: #374151; }
tr:last-child td { border-bottom: none; }
.role-chip { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.role-chip.manager { background: #dbeafe; color: #1d4ed8; }
.role-chip.worker  { background: #ede9fe; color: #6d28d9; }
.name { font-weight: 600; color: #111827; }
.sub { font-size: 11px; color: #9ca3af; margin-top: 2px; }
.tags { display: flex; flex-wrap: wrap; gap: 4px; }
.tag { background: #dbeafe; color: #1e40af; padding: 2px 7px; border-radius: 99px; font-size: 11px; }
.bar-wrap { display: flex; align-items: center; gap: 6px; }
.bar { height: 6px; border-radius: 3px; min-width: 2px; }
.cap { background: #2563eb; }
.load { background: #f59e0b; }
.bar-label { font-size: 11px; color: #6b7280; white-space: nowrap; }
.hours { font-size: 12px; color: #6b7280; white-space: nowrap; }
.actions { display: flex; gap: 6px; white-space: nowrap; }
.btn-sm { padding: 4px 10px; font-size: 12px; border-radius: 5px; cursor: pointer; border: 1px solid #d1d5db; background: #fff; color: #374151; }
.btn-sm:hover:not(:disabled) { background: #f9fafb; }
.btn-sm.danger { color: #dc2626; border-color: #fca5a5; }
.btn-sm.danger:hover:not(:disabled) { background: #fee2e2; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.empty { text-align: center; color: #9ca3af; font-size: 14px; margin-top: 60px; }
.error-box { background: #fee2e2; color: #991b1b; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.dismiss { background: none; border: none; color: #991b1b; cursor: pointer; font-size: 14px; }
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 12px; padding: 28px; width: 600px; max-width: 95vw; max-height: 90vh; overflow-y: auto; }
.modal-title { font-size: 18px; font-weight: 700; color: #111827; margin: 0 0 20px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-grid label { display: flex; flex-direction: column; font-size: 12px; font-weight: 600; color: #6b7280; gap: 4px; }
.form-grid label.full { grid-column: 1 / -1; }
.form-grid input { padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 13px; color: #111827; outline: none; }
.form-grid input:focus { border-color: #2563eb; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
</style>
