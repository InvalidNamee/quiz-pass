<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page } from '../api/client'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppPagination from '../components/AppPagination.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'

type GenerationJob = {
  id: number
  bank_id: number | null
  type: string
  status: string
  file_name: string | null
  ai_model_snapshot: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

const route = useRoute()
const router = useRouter()
const jobs = ref<GenerationJob[]>([])
const status = ref('')
const pageInfo = ref<Page<GenerationJob> | null>(null)
const loading = ref(true)

async function load() {
  status.value = String(route.query.status || '')
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (status.value) params.set('status', status.value)
  loading.value = true
  try {
    const data = await api<Page<GenerationJob>>(`/api/v1/ai-generation/jobs?${params}`)
    pageInfo.value = data
    jobs.value = data.items
  } finally {
    loading.value = false
  }
}

function applyFilters(page = 1) {
  const query: Record<string, string> = {}
  if (page > 1) query.page = String(page)
  if (status.value) query.status = status.value
  router.push({ query })
}

function statusBadge(value: string): 'default' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    pending: 'default', processing: 'info', succeeded: 'success', failed: 'danger',
  }
  return map[value] || 'default'
}

function statusText(value: string) {
  const map: Record<string, string> = { pending: '等待生成', processing: '生成中', succeeded: '生成成功', failed: '生成失败' }
  return map[value] || value
}

function typeText(value: string) {
  return value === 'bank_parse_ai' ? '题库解析' : value === 'document_ai' ? '知识库生成' : value
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold">生成队列</h1>
          <p class="mt-2 text-slate-600">查看 AI 生成题库任务。</p>
        </div>
        <RouterLink to="/banks/generate" class="inline-flex items-center rounded-btn bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">新建题库</RouterLink>
      </div>
      <div class="mt-5 flex flex-wrap gap-2">
        <select v-model="status" class="rounded-input border border-slate-300 bg-white px-3 py-2">
          <option value="">全部状态</option>
          <option value="pending">等待生成</option>
          <option value="processing">生成中</option>
          <option value="succeeded">生成成功</option>
          <option value="failed">生成失败</option>
        </select>
        <AppButton @click="applyFilters()">筛选</AppButton>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!jobs.length" title="暂无生成任务" />

    <template v-else>
      <div class="grid gap-3">
        <RouterLink
          v-for="job in jobs"
          :key="job.id"
          class="page-card p-5 hover:border-brand-500/30"
          :to="job.bank_id ? `/banks/${job.bank_id}` : '/banks'"
        >
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <strong>任务 #{{ job.id }}</strong>
                <AppBadge variant="default">{{ typeText(job.type) }}</AppBadge>
                <AppBadge :variant="statusBadge(job.status)">{{ statusText(job.status) }}</AppBadge>
              </div>
              <p class="mt-2 text-sm text-slate-600">{{ job.file_name || '未记录文件名' }}</p>
            </div>
            <span class="text-sm text-slate-500">{{ job.ai_model_snapshot || '未记录模型' }}</span>
          </div>
          <pre v-if="job.error_message" class="mt-3 whitespace-pre-wrap rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">{{ job.error_message }}</pre>
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
