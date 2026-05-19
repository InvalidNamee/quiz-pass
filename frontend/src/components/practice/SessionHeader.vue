<script setup lang="ts">
defineProps<{
  currentIndex: number
  totalQuestions: number
}>()

const emit = defineEmits<{ submit: [] }>()
</script>

<template>
  <div class="qp-titlebar">
    <h1 class="qp-title">第 {{ currentIndex + 1 }} / {{ totalQuestions }} 题</h1>
    <el-button type="primary" @click="emit('submit')">交卷</el-button>
  </div>
</template>
