<script setup lang="ts">
import { watch, ref } from 'vue'
import { getWorkflowDetail, type WorkflowDetail, type WorkflowListItem } from '../api/v2/aiGeneration'
import { useToast } from '../composables/useToast'

const props = withDefaults(defineProps<{
  modelValue: boolean
  workflow: WorkflowListItem | null
  showActions?: boolean
}>(), {
  showActions: true,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  retry: [workflow: WorkflowListItem]
  cancel: [workflow: WorkflowListItem]
}>()

const toast = useToast()
const detail = ref<WorkflowDetail | null>(null)
const loading = ref(false)

function statusText(value: string) {
  const map: Record<string, string> = {
    pending: '等待生成',
    extracting_document: '提取文档',
    calling_model: '调用模型',
    validating: '校验中',
    repairing: '自动修复',
    draft_ready: '草稿待确认',
    imported: '已入库',
    failed: '生成失败',
    cancelled: '已取消',
  }
  return map[value] || value
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString() : '-'
}

function jsonPreview(value: string | null) {
  if (!value) return ''
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}

async function load() {
  if (!props.modelValue || !props.workflow) return
  loading.value = true
  try {
    detail.value = await getWorkflowDetail(props.workflow.id)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '加载详情失败', 'error')
  } finally {
    loading.value = false
  }
}

watch(() => [props.modelValue, props.workflow?.id], load, { immediate: true })
</script>

<template>
  <el-drawer :model-value="modelValue" title="生成详情" size="760px" @update:model-value="emit('update:modelValue', $event)">
    <div v-loading="loading" class="grid gap-3">
      <template v-if="detail">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="任务 ID">#{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusText(detail.status) }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ detail.ai_model_snapshot || '-' }}</el-descriptions-item>
          <el-descriptions-item label="修复次数">{{ detail.repair_attempts }}</el-descriptions-item>
          <el-descriptions-item label="队列任务">{{ detail.queue_job_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="入队时间">{{ formatTime(detail.enqueued_at) }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ formatTime(detail.started_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(detail.finished_at) }}</el-descriptions-item>
          <el-descriptions-item label="源文件">{{ detail.source_file_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="上下文">
            {{ detail.inherit_context ? '使用题库 AI 描述' : '不使用题库 AI 描述' }} ·
            {{ detail.include_existing_questions ? '附带已有题干' : '不附带已有题干' }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="showActions" class="flex flex-wrap gap-2">
          <el-button v-if="detail.can_retry" size="small" @click="emit('retry', detail)">重新生成</el-button>
          <el-button v-if="detail.can_cancel" size="small" type="danger" plain @click="emit('cancel', detail)">撤销</el-button>
          <RouterLink v-if="detail.can_confirm" :to="`/ai-generation/workflows/${detail.id}/draft`">
            <el-button size="small" type="primary">确认草稿</el-button>
          </RouterLink>
        </div>

        <el-collapse>
          <el-collapse-item title="源文本快照" name="source">
            <pre class="max-h-80 overflow-auto whitespace-pre-wrap text-xs">{{ detail.source_text_snapshot || '无' }}</pre>
          </el-collapse-item>
          <el-collapse-item title="额外指令" name="extra">
            <pre class="whitespace-pre-wrap text-xs">{{ detail.extra_instruction || '无' }}</pre>
          </el-collapse-item>
          <el-collapse-item v-if="detail.error_message" title="完整错误" name="error">
            <pre class="max-h-72 overflow-auto whitespace-pre-wrap text-xs text-red-700">{{ detail.error_message }}</pre>
          </el-collapse-item>
        </el-collapse>

        <el-timeline>
          <el-timeline-item v-for="step in detail.steps" :key="step.id" :timestamp="formatTime(step.finished_at || step.created_at)" :type="step.status === 'failed' ? 'danger' : 'success'">
            <div class="grid gap-1">
              <strong>{{ step.step_name }} · {{ step.status }}</strong>
              <pre v-if="step.error_message" class="max-h-40 overflow-auto whitespace-pre-wrap text-xs text-red-700">{{ step.error_message }}</pre>
              <el-collapse v-if="step.input_json || step.output_json">
                <el-collapse-item title="输入/输出 JSON" :name="String(step.id)">
                  <pre v-if="step.input_json" class="max-h-40 overflow-auto whitespace-pre-wrap text-xs">输入：{{ jsonPreview(step.input_json) }}</pre>
                  <pre v-if="step.output_json" class="max-h-40 overflow-auto whitespace-pre-wrap text-xs">输出：{{ jsonPreview(step.output_json) }}</pre>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-timeline-item>
        </el-timeline>
      </template>
      <el-empty v-else-if="!loading" description="暂无详情" />
    </div>
  </el-drawer>
</template>
