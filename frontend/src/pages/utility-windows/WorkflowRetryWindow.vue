<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import type { AIProviderConfig } from '../../api/types'
import { getWorkflowDetail, retryWorkflow, type WorkflowListItem } from '../../api/v2/aiGeneration'
import { getBank } from '../../api/v2/banks'
import { listAIConfigs } from '../../api/v2/users'
import { useToast } from '../../composables/useToast'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  workflowId?: number
  requestId?: string
}
type QuestionTypeKey = 'single' | 'multiple' | 'blank' | 'short_answer'

const questionTypeLabels: Record<QuestionTypeKey, string> = { single: '单选', multiple: '多选', blank: '填空', short_answer: '简答' }
const questionTypeRows: Array<{ key: QuestionTypeKey; label: string }> = [
  { key: 'single', label: questionTypeLabels.single },
  { key: 'multiple', label: questionTypeLabels.multiple },
  { key: 'blank', label: questionTypeLabels.blank },
  { key: 'short_answer', label: questionTypeLabels.short_answer },
]
const defaultTypeSettings: Record<QuestionTypeKey, { enabled: boolean; useCount: boolean; count: number }> = {
  single: { enabled: true, useCount: true, count: 5 },
  multiple: { enabled: true, useCount: true, count: 3 },
  blank: { enabled: true, useCount: false, count: 2 },
  short_answer: { enabled: false, useCount: false, count: 1 },
}

const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('workflow-retry')
const loading = ref(true)
const retrying = ref(false)
const workflow = ref<WorkflowListItem | null>(null)
const configs = ref<AIProviderConfig[]>([])
const retryFiles = ref<File[]>([])
const retryForm = ref({
  aiProviderConfigId: '',
  generationMode: 'knowledge_generate',
  generateDescription: false,
  extraInstruction: '',
  inheritContext: true,
  includeExistingQuestions: false,
  sourceText: '',
  title: '',
  description: '',
  aiContext: '',
})
const retryTypeSettings = reactive<Record<QuestionTypeKey, { enabled: boolean; useCount: boolean; count: number }>>({
  single: { ...defaultTypeSettings.single },
  multiple: { ...defaultTypeSettings.multiple },
  blank: { ...defaultTypeSettings.blank },
  short_answer: { ...defaultTypeSettings.short_answer },
})

function configLabel(config: AIProviderConfig) {
  return config.name ? `${config.name} · ${config.model}` : config.model
}

function applyTypeSettings(row: WorkflowListItem) {
  for (const { key } of questionTypeRows) {
    const saved = row.question_type_settings?.[key]
    const fallback = defaultTypeSettings[key]
    const count = typeof saved?.count === 'number' && saved.count > 0 ? saved.count : fallback.count
    retryTypeSettings[key].enabled = typeof saved?.enabled === 'boolean' ? saved.enabled : fallback.enabled
    retryTypeSettings[key].useCount = typeof saved?.count === 'number' && saved.count > 0
    retryTypeSettings[key].count = count
  }
}

async function load() {
  if (!payload.value.workflowId) return
  loading.value = true
  try {
    const [detail, configList] = await Promise.all([
      getWorkflowDetail(Number(payload.value.workflowId)),
      listAIConfigs(),
    ])
    const bankDetail = detail.purpose === 'create_bank' && detail.bank_id ? await getBank(detail.bank_id).catch(() => null) : null
    workflow.value = detail
    configs.value = configList
    retryForm.value = {
      aiProviderConfigId: detail.ai_provider_config_id
        ? String(detail.ai_provider_config_id)
        : String(configList.find((item) => item.is_default)?.id || configList[0]?.id || ''),
      generationMode: detail.generation_mode,
      generateDescription: detail.generate_description === 'true',
      extraInstruction: detail.extra_instruction || '',
      inheritContext: detail.inherit_context,
      includeExistingQuestions: detail.include_existing_questions,
      sourceText: detail.source_text_snapshot || '',
      title: bankDetail?.title || detail.bank_title_snapshot || '重新生成题库',
      description: bankDetail?.description || '',
      aiContext: bankDetail?.ai_context || '',
    }
    applyTypeSettings(detail)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载 workflow 失败', 'error')
  } finally {
    loading.value = false
  }
}

function onUploadChange(_uploadFile: { raw?: File }, uploadFiles: Array<{ raw?: File }>) {
  retryFiles.value = uploadFiles.map((item) => item.raw).filter((item): item is File => Boolean(item))
}

function onUploadRemove(_uploadFile: unknown, uploadFiles: Array<{ raw?: File }>) {
  retryFiles.value = uploadFiles.map((item) => item.raw).filter((item): item is File => Boolean(item))
}

function questionTypeSettingsJson() {
  const payloadData: Record<QuestionTypeKey, { enabled: boolean; count: number | null }> = {
    single: { enabled: retryTypeSettings.single.enabled, count: retryForm.value.generationMode === 'knowledge_generate' && retryTypeSettings.single.useCount ? retryTypeSettings.single.count : null },
    multiple: { enabled: retryTypeSettings.multiple.enabled, count: retryForm.value.generationMode === 'knowledge_generate' && retryTypeSettings.multiple.useCount ? retryTypeSettings.multiple.count : null },
    blank: { enabled: retryTypeSettings.blank.enabled, count: retryForm.value.generationMode === 'knowledge_generate' && retryTypeSettings.blank.useCount ? retryTypeSettings.blank.count : null },
    short_answer: { enabled: retryTypeSettings.short_answer.enabled, count: retryForm.value.generationMode === 'knowledge_generate' && retryTypeSettings.short_answer.useCount ? retryTypeSettings.short_answer.count : null },
  }
  if (!Object.values(payloadData).some((item) => item.enabled)) {
    toast.show('至少启用一种题型', 'error')
    return null
  }
  return JSON.stringify(payloadData)
}

async function submitRetry() {
  if (!workflow.value) return
  if (!retryFiles.value.length && !retryForm.value.sourceText.trim()) {
    toast.show('请填写源文本或重新上传文件', 'error')
    return
  }
  retrying.value = true
  try {
    const form = new FormData()
    if (retryForm.value.aiProviderConfigId) form.set('ai_provider_config_id', retryForm.value.aiProviderConfigId)
    form.set('generation_mode', retryForm.value.generationMode)
    const typeSettings = questionTypeSettingsJson()
    if (!typeSettings) return
    form.set('question_type_settings', typeSettings)
    form.set('question_count_mode', 'adaptive')
    form.set('generate_description', String(retryForm.value.generateDescription))
    form.set('extra_instruction', retryForm.value.extraInstruction)
    form.set('inherit_context', String(workflow.value.purpose === 'extend_bank' ? retryForm.value.inheritContext : false))
    form.set('include_existing_questions', String(workflow.value.purpose === 'extend_bank' ? retryForm.value.includeExistingQuestions : false))
    if (workflow.value.purpose === 'create_bank') {
      form.set('title', retryForm.value.title || '重新生成题库')
      form.set('description', retryForm.value.description)
      form.set('ai_context', retryForm.value.aiContext)
    }
    if (retryFiles.value.length) retryFiles.value.forEach((item) => form.append('files', item))
    else form.set('source_text', retryForm.value.sourceText.trim())
    const data = await retryWorkflow(workflow.value.id, form)
    toast.show(`已创建重新生成 workflow #${data.workflow_id}`, 'success')
    await complete('workflow-retried', data)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '重新生成失败', 'error')
  } finally {
    retrying.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading" class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">重新生成</h1>
        <p class="mt-1 text-sm text-slate-500">基于原 workflow 输入创建新的生成分支，旧记录会保留。</p>
      </div>

      <el-form v-if="workflow" label-position="top">
        <el-form-item label="生成模式">
          <el-radio-group v-model="retryForm.generationMode">
            <el-radio-button value="knowledge_generate">从知识库生成</el-radio-button>
            <el-radio-button value="bank_parse">从题库解析</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="workflow.purpose === 'create_bank'" label="题库名称">
          <el-input v-model="retryForm.title" placeholder="重新生成题库" />
        </el-form-item>
        <el-form-item v-if="workflow.purpose === 'create_bank'" label="题库描述">
          <el-input v-model="retryForm.description" type="textarea" :rows="2" placeholder="简短描述（可选）" />
        </el-form-item>
        <el-form-item v-if="workflow.purpose === 'create_bank'" label="AI 背景知识（给 AI 看，可选）">
          <el-input v-model="retryForm.aiContext" type="textarea" :rows="3" maxlength="12000" show-word-limit placeholder="重新生成会继续写回同一个题库壳。" />
        </el-form-item>

        <el-form-item label="AI 模型">
          <el-select v-model="retryForm.aiProviderConfigId" class="w-full">
            <el-option v-for="config in configs" :key="config.id" :value="String(config.id)" :label="configLabel(config)" />
          </el-select>
        </el-form-item>

        <el-form-item label="题型配置">
          <div class="w-full overflow-hidden rounded-lg border border-slate-200">
            <div v-for="row in questionTypeRows" :key="row.key" class="grid grid-cols-[96px_1fr_140px] items-center gap-3 border-b border-slate-100 px-3 py-2 last:border-b-0">
              <el-checkbox v-model="retryTypeSettings[row.key].enabled">{{ row.label }}</el-checkbox>
              <el-checkbox v-if="retryForm.generationMode === 'knowledge_generate'" v-model="retryTypeSettings[row.key].useCount" :disabled="!retryTypeSettings[row.key].enabled">限定数量</el-checkbox>
              <span v-else class="text-xs text-slate-500">解析该题型</span>
              <el-input-number v-if="retryForm.generationMode === 'knowledge_generate'" v-model="retryTypeSettings[row.key].count" size="small" :min="1" :max="100" :disabled="!retryTypeSettings[row.key].enabled || !retryTypeSettings[row.key].useCount" />
            </div>
          </div>
        </el-form-item>

        <el-form-item v-if="workflow.purpose === 'extend_bank'">
          <el-checkbox v-model="retryForm.inheritContext">使用题库 AI 描述</el-checkbox>
        </el-form-item>
        <el-form-item v-if="workflow.purpose === 'extend_bank'">
          <el-checkbox v-model="retryForm.includeExistingQuestions">附带已有题目题干给 AI</el-checkbox>
        </el-form-item>
        <el-form-item v-if="retryForm.generationMode === 'knowledge_generate'">
          <el-checkbox v-model="retryForm.generateDescription">让 AI 生成题库描述</el-checkbox>
        </el-form-item>
        <el-form-item label="额外指令">
          <el-input v-model="retryForm.extraInstruction" type="textarea" :rows="3" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="源文本">
          <el-input v-model="retryForm.sourceText" type="textarea" :rows="8" placeholder="可直接编辑上次提取文本；也可以上传新文件替换" />
        </el-form-item>
        <el-form-item label="替换文件（可选）">
          <el-upload
            :auto-upload="false"
            :limit="20"
            multiple
            accept=".txt,.docx,.pdf"
            :on-change="onUploadChange"
            :on-remove="onUploadRemove"
          >
            <el-button>选择文件</el-button>
            <template #tip><span class="ml-2 text-sm text-slate-500">支持 .txt / .docx / .pdf，可上传多个文件；上传后将替换上方源文本。</span></template>
          </el-upload>
        </el-form-item>
      </el-form>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">取消</el-button>
        <el-button type="primary" :loading="retrying" @click="submitRetry">重新生成</el-button>
      </div>
    </div>
  </section>
</template>
