<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page, type PracticeSession } from '../api/client'

const route = useRoute()
const router = useRouter()
const sessions = ref<PracticeSession[]>([])
const mode = ref('')
const status = ref('')
const pageInfo = ref<Page<PracticeSession> | null>(null)

async function load() {
  mode.value = String(route.query.mode || '')
  status.value = String(route.query.status || '')
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (mode.value) params.set('mode', mode.value)
  if (status.value) params.set('status', status.value)
  const data = await api<Page<PracticeSession>>(`/api/v1/history/sessions?${params}`)
  pageInfo.value = data
  sessions.value = data.items
}

function applyFilters(page = 1) {
  const query: Record<string, string> = {}
  if (page > 1) query.page = String(page)
  if (mode.value) query.mode = mode.value
  if (status.value) query.status = status.value
  router.push({ query })
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">练习历史</h1>
    <div class="my-4 grid max-w-xl gap-3 sm:grid-cols-[1fr_1fr_auto]">
      <select v-model="mode" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="">全部模式</option>
        <option value="practice">普通练习</option>
        <option value="exam">模拟考试</option>
        <option value="mistake_review">错题练习</option>
      </select>
      <select v-model="status" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="">全部状态</option>
        <option value="in_progress">进行中</option>
        <option value="submitted">已提交</option>
      </select>
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="applyFilters()">筛选</button>
    </div>
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
    <div v-if="pageInfo" class="mt-4 flex items-center justify-end gap-3 text-sm text-slate-600">
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page <= 1" @click="applyFilters(pageInfo.page - 1)">上一页</button>
      <span>第 {{ pageInfo.page }} / {{ pageInfo.total_pages || 1 }} 页，共 {{ pageInfo.total }} 个</span>
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page >= pageInfo.total_pages" @click="applyFilters(pageInfo.page + 1)">下一页</button>
    </div>
  </section>
</template>
