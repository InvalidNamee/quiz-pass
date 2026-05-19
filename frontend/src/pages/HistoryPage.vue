<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listHistory } from '../api/practice'
import type { Page, PracticeSession } from '../api/types'
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
  const map: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = { practice: 'info', exam: 'warning', mistake_review: 'danger' }
  return map[m] || 'default'
}
function modeText(m: string) {
  const map: Record<string, string> = { practice: '练习', exam: '考试', mistake_review: '错题' }
  return map[m] || m
}
function formatTime(value: string | null) {
  if (!value) return ''
  return new Date(value).toLocaleString()
}
function activityDesc(item: PracticeSession) {
  if (item.submitted_at) return `交卷 ${formatTime(item.submitted_at)}`
  if (item.last_answered_at) return `最近 ${formatTime(item.last_answered_at)}`
  return formatTime(item.started_at)
}

async function load() {
  mode.value = String(route.query.mode || '')
  status.value = String(route.query.status || '')
  loading.value = true
  try {
    const data = await listHistory({ page: Number(route.query.page || 1), mode: mode.value || undefined, status: status.value || undefined })
    pageInfo.value = data; sessions.value = data.items
  } finally { loading.value = false }
}

function applyFilters(page = 1) {
  const q: Record<string, string> = {}
  if (page > 1) q.page = String(page)
  if (mode.value) q.mode = mode.value
  if (status.value) q.status = status.value
  router.push({ query: q })
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-4">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-lg font-bold">刷题记录</h1>
      <div class="flex flex-wrap gap-2">
        <select v-model="mode" class="rounded-input border border-slate-300 bg-white px-2 py-1.5 text-sm">
          <option value="">全部模式</option>
          <option value="practice">普通练习</option>
          <option value="exam">模拟考试</option>
          <option value="mistake_review">错题复习</option>
        </select>
        <select v-model="status" class="rounded-input border border-slate-300 bg-white px-2 py-1.5 text-sm">
          <option value="">全部状态</option>
          <option value="in_progress">进行中</option>
          <option value="submitted">已提交</option>
        </select>
        <AppButton size="sm" @click="applyFilters()">筛选</AppButton>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!sessions.length" title="暂无练习记录" />

    <template v-else>
      <div class="divide-y divide-slate-100 border-y border-slate-200 text-sm">
        <RouterLink
          v-for="item in sessions" :key="item.id"
          class="flex flex-wrap items-center justify-between gap-3 py-2.5 hover:bg-slate-50"
          :to="item.status === 'in_progress' ? `/practice/session/${item.id}` : `/practice/result/${item.id}`"
        >
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-1.5">
              <RouterLink :to="`/banks/${item.bank_id}`" class="font-medium text-slate-900 hover:text-brand-600 truncate" @click.stop>{{ item.bank_title || `题库 #${item.bank_id}` }}</RouterLink>
              <AppBadge v-if="item.bank_visibility === 'public'" variant="default" size="sm">公开</AppBadge>
            </div>
            <span class="text-xs text-slate-400">{{ activityDesc(item) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <AppBadge :variant="modeBadge(item.mode)">{{ modeText(item.mode) }}</AppBadge>
            <AppBadge :variant="item.status === 'submitted' ? 'success' : 'warning'">{{ item.status === 'submitted' ? '已提交' : '进行中' }}</AppBadge>
            <span v-if="item.status === 'in_progress'" class="text-xs text-slate-500">{{ item.answered_count }}/{{ item.total_questions }}</span>
            <span v-else class="text-xs font-medium" :class="(item.score || 0) >= 80 ? 'text-emerald-600' : (item.score || 0) >= 60 ? 'text-yellow-600' : 'text-red-600'">{{ item.score }} · {{ item.correct_count }}/{{ item.total_questions }}</span>
          </div>
        </RouterLink>
      </div>
      <AppPagination v-if="pageInfo && pageInfo.total_pages > 1" :page="pageInfo.page" :total-pages="pageInfo.total_pages" :total="pageInfo.total" @update:page="applyFilters" />
    </template>
  </section>
</template>
