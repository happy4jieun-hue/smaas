<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { createTask } from "../api/tasks";

const router = useRouter();

const title = ref("");
const description = ref("");
const loading = ref(false);
const error = ref<string | null>(null);

async function handleSubmit() {
  error.value = null;
  if (!title.value.trim()) {
    error.value = "title은 필수입니다.";
    return;
  }
  loading.value = true;
  try {
    const task = await createTask({
      title: title.value,
      description: description.value,
    });
    // [DEBUG] task.id 길이 확인 — UUID는 항상 36자여야 함
    console.log(`[CreateTask] task.id="${task.id}" length=${task.id?.length}`);
    router.push(`/workflows/${task.id}`);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "오류가 발생했습니다.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="wrapper">
    <h1 class="title">Task 생성</h1>
    <form @submit.prevent="handleSubmit" class="form">
      <label class="label">
        Title *
        <input
          v-model="title"
          placeholder="업무 제목을 입력하세요"
          class="input"
        />
      </label>

      <label class="label">
        Description
        <textarea
          v-model="description"
          placeholder="업무 상세 설명과 기한을 입력하세요"
          rows="5"
          class="input textarea"
        />
      </label>

      <div v-if="error" class="error">{{ error }}</div>

      <button type="submit" :disabled="loading" class="button">
        {{ loading ? "생성 중..." : "생성" }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.wrapper {
  max-width: 560px;
  margin: 60px auto;
  padding: 0 20px;
  font-family: "Segoe UI", sans-serif;
}
.title {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  margin-bottom: 28px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}
.input {
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid #d1d5db;
  font-size: 14px;
  color: #111827;
  outline: none;
  font-family: inherit;
}
.textarea {
  resize: vertical;
}
.error {
  background: #fee2e2;
  color: #991b1b;
  padding: 10px 14px;
  border-radius: 6px;
  font-size: 13px;
}
.button {
  padding: 12px 0;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}
.button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
