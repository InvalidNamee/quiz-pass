<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page } from '../api/client'

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

async function load() {
  status.value = String(route.query.status || '')
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (status.value) params.set('status', status.value)
  const data = await api<Page<GenerationJob>>(`/api/v1/ai-generation/jobs?${params}`)
  pageInfo.value = data
  jobs.value = data.items
}

function applyFilters(page = 1) {
  const query: Record<string, string> = {}
  if (page > 1) query.page = String(page)
  if (status.value) query.status = status.value
  router.push({ query })
}

function statusText(value: string) {
  const map: Record<string, string> = {
    pending: '等待生成',
    processing: '生成中',
    succeeded: '生成成功',
    failed: '生成失败',
  }
  return map[value] || value
}

function statusClass(value: string) {
  if (value === 'succeeded') return 'bg-green-50 text-green-800'
  if (value === 'failed') return 'bg-red-50 text-red-800'
  if (value === 'processing') return 'bg-blue-50 text-blue-800'
  return 'bg-slate-100 text-slate-700'
}

function typeText(value: string) {
  if (value === 'bank_parse_ai') return '题库解析'
  if (value === 'document_ai') return '知识库生成'
  return value
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-5">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold">生成队列</h1>
          <p class="mt-2 text-slate-600">查看 AI 生成题库任务的状态、模型和失败原因。</p>
        </div>
        <RouterLink class="rounded-md bg-blue-600 px-4 py-2 text-white" to="/banks/generate">新建题库</RouterLink>
      </div>
      <div class="mt-5 flex flex-wrap gap-2">
        <select v-model="status" class="rounded-md border border-slate-300 bg-white px-3 py-2">
          <option value="">全部状态</option>
          <option value="pending">等待生成</option>
          <option value="processing">生成中</option>
          <option value="succeeded">生成成功</option>
          <option value="failed">生成失败</option>
        </select>
        <button class="rounded-md bg-slate-900 px-4 py-2 text-white" @click="applyFilters()">筛选</button>
      </div>
    </div>

    <div class="grid gap-3">
      <RouterLink
        v-for="job in jobs"
        :key="job.id"
        class="rounded-xl border border-slate-200 bg-white p-5 hover:border-blue-300"
        :to="job.bank_id ? `/banks/${job.bank_id}` : '/banks'"
      >
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <strong>任务 #{{ job.id }}</strong>
              <span class="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-700">{{ typeText(job.type) }}</span>
              <span class="rounded-full px-2 py-1 text-xs" :class="statusClass(job.status)">{{ statusText(job.status) }}</span>
            </div>
            <p class="mt-2 text-sm text-slate-600">{{ job.file_name || '未记录文件名' }}</p>
          </div>
          <span class="text-sm text-slate-500">{{ job.ai_model_snapshot || '未记录模型' }}</span>
        </div>
        <pre v-if="job.error_message" class="mt-3 whitespace-pre-wrap rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">{{ job.error_message }}</pre>
      </RouterLink>
      <div v-if="!jobs.length" class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">暂无生成任务</div>
    </div>

    <div v-if="pageInfo" class="flex items-center justify-end gap-3 text-sm text-slate-600">
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page <= 1" @click="applyFilters(pageInfo.page - 1)">上一页</button>
      <span>第 {{ pageInfo.page }} / {{ pageInfo.total_pages || 1 }} 页，共 {{ pageInfo.total }} 个</span>
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page >= pageInfo.total_pages" @click="applyFilters(pageInfo.page + 1)">下一页</button>
    </div>
  </section>
</template>
