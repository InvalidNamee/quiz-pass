<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Page, type PracticeSession } from '../api/client'

const sessions = ref<PracticeSession[]>([])

async function load() {
  const data = await api<Page<PracticeSession>>('/api/v1/history/sessions')
  sessions.value = data.items
}

onMounted(load)
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">练习历史</h1>
    <div class="mt-4 grid gap-3">
      <RouterLink
        v-for="item in sessions"
        :key="item.id"
        class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
        :to="item.status === 'in_progress' ? `/practice/session/${item.id}` : `/practice/result/${item.id}`"
      >
        <strong>#{{ item.id }} · {{ item.mode }}</strong>
        <span v-if="item.status === 'in_progress'" class="text-sm text-slate-500">{{ item.status }} · 已做 {{ item.answered_count }} / {{ item.total_questions }}</span>
        <span v-else class="text-sm text-slate-500">{{ item.status }} · {{ item.score }} 分 · {{ item.correct_count }}/{{ item.total_questions }}</span>
      </RouterLink>
    </div>
  </section>
</template>
