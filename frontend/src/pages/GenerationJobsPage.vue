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
  workflow_id: number | null
  type: string
  status: string
  workflow_status: string | null
  draft_question_count: number
  repair_attempts: number
  can_confirm: boolean
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
    pending: 'default',
    processing: 'info',
    extracting_document: 'info',
    calling_model: 'info',
    validating: 'info',
    repairing: 'warning',
    draft_ready: 'warning',
    imported: 'success',
    succeeded: 'success',
    failed: 'danger',
    cancelled: 'default',
  }
  return map[value] || 'default'
}

function statusText(value: string) {
  const map: Record<string, string> = {
    pending: '等待生成',
    processing: '生成中',
    extracting_document: '提取文档',
    calling_model: '调用模型',
    validating: '校验中',
    repairing: '自动修复',
    draft_ready: '草稿待确认',
    imported: '已入库',
    succeeded: '生成成功',
    failed: '生成失败',
    cancelled: '已取消',
  }
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
          <option value="calling_model">调用模型</option>
          <option value="validating">校验中</option>
          <option value="repairing">自动修复</option>
          <option value="draft_ready">草稿待确认</option>
          <option value="imported">已入库</option>
          <option value="failed">生成失败</option>
        </select>
        <AppButton @click="applyFilters()">筛选</AppButton>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!jobs.length" title="暂无生成任务" />

    <template v-else>
      <div class="grid gap-3">
        <div
          v-for="job in jobs"
          :key="job.id"
          class="page-card p-5 hover:border-brand-500/30"
        >
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <strong>任务 #{{ job.id }}</strong>
                <AppBadge variant="default">{{ typeText(job.type) }}</AppBadge>
                <AppBadge :variant="statusBadge(job.status)">{{ statusText(job.status) }}</AppBadge>
              </div>
              <p class="mt-2 text-sm text-slate-600">
                {{ job.file_name || '未记录文件名' }}
                <span v-if="job.draft_question_count"> · 草稿 {{ job.draft_question_count }} 题</span>
                <span v-if="job.repair_attempts"> · 修复 {{ job.repair_attempts }} 次</span>
              </p>
            </div>
            <span class="text-sm text-slate-500">{{ job.ai_model_snapshot || '未记录模型' }}</span>
          </div>
          <div class="mt-4 flex flex-wrap gap-2">
            <RouterLink
              v-if="job.can_confirm"
              :to="`/ai-generation/jobs/${job.id}/draft`"
              class="inline-flex items-center rounded-btn bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              确认草稿
            </RouterLink>
            <RouterLink
              v-if="job.bank_id"
              :to="`/banks/${job.bank_id}`"
              class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200"
            >
              查看题库
            </RouterLink>
          </div>
          <pre v-if="job.error_message" class="mt-3 whitespace-pre-wrap rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">{{ job.error_message }}</pre>
        </div>
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
