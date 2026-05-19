<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Page } from '../api/types'
import { listWorkflows, type WorkflowListItem } from '../api/v2/aiGeneration'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppPagination from '../components/AppPagination.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'

const route = useRoute()
const router = useRouter()
const jobs = ref<WorkflowListItem[]>([])
const status = ref('')
const pageInfo = ref<Page<WorkflowListItem> | null>(null)
const loading = ref(true)

async function load() {
  status.value = String(route.query.status || '')
  loading.value = true
  try {
    const data = await listWorkflows({ page: Number(route.query.page || 1), status: status.value || undefined })
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

function typeText(item: WorkflowListItem) {
  const mode = item.generation_mode === 'bank_parse' ? '题库解析' : '知识库生成'
  const purpose = item.purpose === 'extend_bank' ? '扩展题库' : '新建题库'
  return `${purpose} · ${mode}`
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-5">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h1 class="text-lg font-bold">生成队列</h1>
      <div class="flex flex-wrap gap-2">
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
        <AppButton size="sm" @click="applyFilters()">筛选</AppButton>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!jobs.length" title="暂无生成任务" />

    <template v-else>
      <div class="divide-y divide-slate-100 border-y border-slate-200">
        <div v-for="job in jobs" :key="job.id" class="py-2.5">
          <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
            <div class="flex items-center gap-2">
              <span class="font-medium">#{{ job.id }}</span>
              <AppBadge variant="default">{{ typeText(job) }}</AppBadge>
              <AppBadge :variant="statusBadge(job.status)">{{ statusText(job.status) }}</AppBadge>
              <span class="text-xs text-slate-500">{{ job.source_file_name || '未记录' }}</span>
              <span v-if="job.draft_question_count" class="text-xs text-slate-400">{{ job.draft_question_count }} 题</span>
              <span v-if="job.repair_attempts" class="text-xs text-slate-400">修复{{ job.repair_attempts }}次</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs text-slate-400">{{ job.ai_model_snapshot || '' }}</span>
              <RouterLink v-if="job.can_confirm" :to="`/ai-generation/workflows/${job.id}/draft`" class="rounded-btn bg-brand-600 px-2 py-1 text-xs font-medium text-white hover:bg-brand-700">确认草稿</RouterLink>
              <RouterLink v-if="job.bank_id" :to="`/banks/${job.bank_id}`" class="rounded-btn bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700 hover:bg-slate-200">查看题库</RouterLink>
            </div>
          </div>
          <pre v-if="job.error_message" class="mt-2 whitespace-pre-wrap rounded bg-red-50 px-3 py-2 text-xs text-red-800">{{ job.error_message }}</pre>
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
