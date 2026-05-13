<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page, type PracticeSession } from '../api/client'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppPagination from '../components/AppPagination.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'

const route = useRoute()
const router = useRouter()
const sessions = ref<PracticeSession[]>([])
const mode = ref('')
const status = ref('')
const pageInfo = ref<Page<PracticeSession> | null>(null)
const loading = ref(true)

function modeBadge(m: string): 'default' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    practice: 'info', exam: 'warning', mistake_review: 'danger',
  }
  return map[m] || 'default'
}

function modeText(m: string) {
  const map: Record<string, string> = { practice: '普通练习', exam: '模拟考试', mistake_review: '错题复习' }
  return map[m] || m
}

async function load() {
  mode.value = String(route.query.mode || '')
  status.value = String(route.query.status || '')
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (mode.value) params.set('mode', mode.value)
  if (status.value) params.set('status', status.value)
  loading.value = true
  try {
    const data = await api<Page<PracticeSession>>(`/api/v1/history/sessions?${params}`)
    pageInfo.value = data
    sessions.value = data.items
  } finally {
    loading.value = false
  }
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
  <section class="grid gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">练习历史</h1>
      <p class="mt-1 text-slate-600">回顾你的练习记录和成绩。</p>
      <div class="mt-5 grid max-w-xl gap-3 sm:grid-cols-[1fr_1fr_auto]">
        <select v-model="mode" class="rounded-input border border-slate-300 bg-white px-3 py-2">
          <option value="">全部模式</option>
          <option value="practice">普通练习</option>
          <option value="exam">模拟考试</option>
          <option value="mistake_review">错题复习</option>
        </select>
        <select v-model="status" class="rounded-input border border-slate-300 bg-white px-3 py-2">
          <option value="">全部状态</option>
          <option value="in_progress">进行中</option>
          <option value="submitted">已提交</option>
        </select>
        <AppButton @click="applyFilters()">筛选</AppButton>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!sessions.length" title="暂无练习记录" description="选择一个题库开始练习吧" />

    <template v-else>
      <div class="grid gap-3">
        <RouterLink
          v-for="item in sessions"
          :key="item.id"
          class="page-card flex items-center justify-between gap-4 p-4"
          :to="item.status === 'in_progress' ? `/practice/session/${item.id}` : `/practice/result/${item.id}`"
        >
          <div class="flex items-center gap-3">
            <strong>#{{ item.id }}</strong>
            <AppBadge :variant="modeBadge(item.mode)">{{ modeText(item.mode) }}</AppBadge>
            <AppBadge :variant="item.status === 'submitted' ? 'success' : 'warning'">{{ item.status === 'submitted' ? '已提交' : '进行中' }}</AppBadge>
          </div>
          <span v-if="item.status === 'in_progress'" class="text-sm text-slate-500">已做 {{ item.answered_count }} / {{ item.total_questions }}</span>
          <span v-else class="text-sm text-slate-500">{{ item.score }} 分 · {{ item.correct_count }}/{{ item.total_questions }}</span>
        </RouterLink>
      </div>

      <AppPagination
        v-if="pageInfo"
        :page="pageInfo.page"
        :total-pages="pageInfo.total_pages || 1"
        :total="pageInfo.total"
        @update:page="applyFilters"
      />
    </template>
  </section>
</template>
