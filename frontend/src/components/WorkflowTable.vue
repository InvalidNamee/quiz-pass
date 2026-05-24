<script setup lang="ts">
import type { WorkflowListItem } from '../api/v2/aiGeneration'
import { formatDateTime } from '../utils/dateTime'

defineProps<{
  workflows: WorkflowListItem[]
  loading?: boolean
  showSensitiveError?: boolean
  showSourceFile?: boolean
  showActions?: boolean
}>()

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
    imported: '已导入',
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

function questionChangeText(row: WorkflowListItem) {
  if (row.status === 'draft_ready' && row.draft_question_count) return `草稿 ${row.draft_question_count} 题`
  if (row.question_delta > 0) return `新增 ${row.question_delta} 题`
  if (row.status === 'failed' || row.status === 'cancelled') return '未导入'
  return '暂无变更'
}

function formatTime(value: string | null) {
  return formatDateTime(value)
}

function visibleError(row: WorkflowListItem, showSensitiveError?: boolean) {
  return showSensitiveError ? row.error_message : row.error_summary
}
</script>

<template>
  <el-table
    v-loading="loading"
    :data="workflows"
    stripe
    size="small"
    highlight-current-row
    empty-text="暂无工作流记录"
    class="border border-slate-100 !rounded-2xl shadow-sm"
  >
    <el-table-column label="#" width="70">
      <template #default="{ row }">
        <span class="font-medium">#{{ row.id }}</span>
      </template>
    </el-table-column>
    <el-table-column label="类型" min-width="140">
      <template #default="{ row }">
        <el-tag>{{ typeText(row) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="状态" width="120">
      <template #default="{ row }">
        <el-tag v-if="statusBadge(row.status) === 'default'">{{ statusText(row.status) }}</el-tag>
        <el-tag v-else :type="statusBadge(row.status)">{{ statusText(row.status) }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column v-if="showSourceFile !== false" label="源文件" min-width="140">
      <template #default="{ row }">
        <span class="text-xs">{{ row.source_file_name || '未记录' }}</span>
      </template>
    </el-table-column>
    <el-table-column label="题目变更" width="120">
      <template #default="{ row }">
        <span class="text-xs text-slate-600">{{ questionChangeText(row) }}</span>
      </template>
    </el-table-column>
    <el-table-column label="详情" width="190">
      <template #default="{ row }">
        <div class="flex flex-wrap gap-x-2 gap-y-0.5">
          <span v-if="row.repair_attempts" class="text-xs text-slate-400">自动修复 {{ row.repair_attempts }} 次</span>
          <span v-if="row.ai_model_snapshot" class="text-xs text-slate-400">{{ row.ai_model_snapshot }}</span>
          <span v-if="row.retried_by_workflow_id" class="text-xs text-slate-400">已被 #{{ row.retried_by_workflow_id }} 取代</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="时间" min-width="180">
      <template #default="{ row }">
        <div class="grid gap-0.5 text-xs text-slate-500">
          <span>创建：{{ formatTime(row.created_at) }}</span>
          <span>完成：{{ formatTime(row.finished_at) }}</span>
        </div>
      </template>
    </el-table-column>
    <el-table-column label="错误" min-width="180" show-overflow-tooltip>
      <template #default="{ row }">
        <el-popover v-if="visibleError(row, showSensitiveError)" placement="top" width="520" trigger="click">
          <pre class="max-h-72 overflow-auto whitespace-pre-wrap text-xs text-red-700">{{ visibleError(row, showSensitiveError) }}</pre>
          <template #reference>
            <el-button link type="danger" size="small">查看失败摘要</el-button>
          </template>
        </el-popover>
      </template>
    </el-table-column>
    <el-table-column v-if="showActions" label="操作" width="300" fixed="right" align="right">
      <template #default="{ row }">
        <slot name="actions" :row="row" />
      </template>
    </el-table-column>
  </el-table>
</template>
