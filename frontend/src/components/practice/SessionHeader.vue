<script setup lang="ts">
defineProps<{
  currentIndex: number
  totalQuestions: number
}>()

const emit = defineEmits<{ submit: [] }>()
</script>

<template>
  <div class="page-card flex items-center justify-between gap-4 p-6">
    <h1 class="text-2xl font-bold">第 {{ currentIndex + 1 }} / {{ totalQuestions }} 题</h1>
    <button class="rounded-btn bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800" @click="emit('submit')">交卷</button>
  </div>
</template>
