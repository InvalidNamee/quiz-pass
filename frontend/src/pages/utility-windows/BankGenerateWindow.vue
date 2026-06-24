<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { UploadInstance } from 'element-plus'
import type { AIProviderConfig, QuestionBankV2 } from '../../api/types'
import { createWorkflow, extendWorkflow } from '../../api/v2/aiGeneration'
import { getBank, importJsonNewBank, importJsonToBank } from '../../api/v2/banks'
import { listAIConfigs } from '../../api/v2/users'
import { useToast } from '../../composables/useToast'
import { normalizeTagNames, tagKey, tagLabel, type TagInputValue } from '../../features/tags/tagUtils'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  extendBankId?: number | null
  requestId?: string
}
type CreateMode = 'ai_knowledge' | 'ai_parse' | 'json_import'
type QuestionTypeKey = 'single' | 'multiple' | 'blank' | 'short_answer'

const questionTypeLabels: Record<QuestionTypeKey, string> = { single: '单选', multiple: '多选', blank: '填空', short_answer: '简答' }
const questionTypeRows: Array<{ key: QuestionTypeKey; label: string }> = [
  { key: 'single', label: questionTypeLabels.single },
  { key: 'multiple', label: questionTypeLabels.multiple },
  { key: 'blank', label: questionTypeLabels.blank },
  { key: 'short_answer', label: questionTypeLabels.short_answer },
]

const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('bank-generate')
const extendBankId = computed(() => payload.value.extendBankId ? Number(payload.value.extendBankId) : null)
const isExtend = computed(() => Boolean(extendBankId.value))
const showNewBankFields = computed(() => !isExtend.value)
const loading = ref(true)
const submitting = ref(false)
const title = ref('')
const description = ref('')
const createMode = ref<CreateMode>('ai_knowledge')
const aiProviderConfigId = ref('')
const questionTypeSettings = reactive<Record<QuestionTypeKey, { enabled: boolean; useCount: boolean; count: number }>>({
  single: { enabled: true, useCount: true, count: 5 },
  multiple: { enabled: true, useCount: true, count: 3 },
  blank: { enabled: true, useCount: false, count: 2 },
  short_answer: { enabled: false, useCount: false, count: 1 },
})
const generateDescription = ref(false)
const extraInstruction = ref('')
const inheritContext = ref(true)
const includeExistingQuestions = ref(false)
const selectedTags = ref<TagInputValue[]>([])
const uploadRef = ref<UploadInstance | null>(null)
const files = ref<File[]>([])
const configs = ref<AIProviderConfig[]>([])
const bank = ref<QuestionBankV2 | null>(null)

function configLabel(config: AIProviderConfig) {
  return config.name ? `${config.name} · ${config.model}` : config.model
}

function fileStem(fileName: string) {
  return fileName.replace(/\.[^/.]+$/, '')
}

async function load() {
  loading.value = true
  try {
    configs.value = await listAIConfigs()
    const preferred = configs.value.find((item) => item.is_default) ?? configs.value[0]
    if (preferred && !aiProviderConfigId.value) aiProviderConfigId.value = String(preferred.id)
    if (extendBankId.value) bank.value = await getBank(extendBankId.value)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载生成配置失败', 'error')
  } finally {
    loading.value = false
  }
}

function reset() {
  title.value = ''
  description.value = ''
  extraInstruction.value = ''
  inheritContext.value = true
  includeExistingQuestions.value = false
  selectedTags.value = []
  files.value = []
}

function serializedQuestionTypeSettings() {
  const result: Record<QuestionTypeKey, { enabled: boolean; count: number | null }> = {
    single: { enabled: questionTypeSettings.single.enabled, count: createMode.value === 'ai_knowledge' && questionTypeSettings.single.useCount ? questionTypeSettings.single.count : null },
    multiple: { enabled: questionTypeSettings.multiple.enabled, count: createMode.value === 'ai_knowledge' && questionTypeSettings.multiple.useCount ? questionTypeSettings.multiple.count : null },
    blank: { enabled: questionTypeSettings.blank.enabled, count: createMode.value === 'ai_knowledge' && questionTypeSettings.blank.useCount ? questionTypeSettings.blank.count : null },
    short_answer: { enabled: questionTypeSettings.short_answer.enabled, count: createMode.value === 'ai_knowledge' && questionTypeSettings.short_answer.useCount ? questionTypeSettings.short_answer.count : null },
  }
  if (!Object.values(result).some((item) => item.enabled)) {
    toast.show('至少启用一种题型', 'error')
    return null
  }
  return JSON.stringify(result)
}

async function prefillFromJson(uploadedFile: File) {
  if (isExtend.value || createMode.value !== 'json_import') return
  try {
    const filePayload = JSON.parse(await uploadedFile.text())
    const bankInfo = filePayload?.bank && typeof filePayload.bank === 'object' ? filePayload.bank : {}
    if (typeof bankInfo.title === 'string' && bankInfo.title.trim()) title.value = bankInfo.title.trim()
    else if (!title.value.trim()) title.value = fileStem(uploadedFile.name)
    if (typeof bankInfo.description === 'string') description.value = bankInfo.description.trim()
    if (Array.isArray(bankInfo.tags)) {
      selectedTags.value = bankInfo.tags
        .filter((tag: unknown): tag is string => typeof tag === 'string' && Boolean(tag.trim()))
        .map((name: string) => name.trim())
    }
  } catch {
    if (!title.value.trim()) title.value = fileStem(uploadedFile.name)
  }
}

async function onUploadChange(uploadFile: { raw?: File }, uploadFiles: Array<{ raw?: File }>) {
  files.value = uploadFiles.map((item) => item.raw).filter((item): item is File => Boolean(item))
  const firstFile = files.value[0] ?? uploadFile.raw
  if (!firstFile) return
  if (!isExtend.value && !title.value.trim()) title.value = fileStem(firstFile.name)
  await prefillFromJson(firstFile)
}

function onUploadRemove(_uploadFile: unknown, uploadFiles: Array<{ raw?: File }>) {
  files.value = uploadFiles.map((item) => item.raw).filter((item): item is File => Boolean(item))
}

async function submit() {
  if (!files.value.length) {
    toast.show('请选择文件', 'error')
    return
  }
  if (!isExtend.value && !title.value.trim()) {
    toast.show('请输入题库名称', 'error')
    return
  }
  submitting.value = true
  try {
    const form = new FormData()
    if (createMode.value === 'json_import') {
      const jsonFile = files.value[0]
      form.set('file', jsonFile)
      const tagNames = normalizeTagNames(selectedTags.value)
      if (tagNames.length) form.set('tag_names', JSON.stringify(tagNames))
      if (!isExtend.value) form.set('file_stem', fileStem(jsonFile.name))
      const importedBank = isExtend.value && extendBankId.value
        ? await importJsonToBank(extendBankId.value, form)
        : await importJsonNewBank(form)
      toast.show(`题目已导入「${importedBank.title}」`, 'success')
      await complete('bank-generate-submitted', { bankId: importedBank.id })
    } else {
      files.value.forEach((item) => form.append('files', item))
      if (!isExtend.value) {
        form.set('title', title.value)
        if (description.value.trim()) form.set('description', description.value.trim())
        const tagNames = normalizeTagNames(selectedTags.value)
        if (tagNames.length) form.set('tag_names', JSON.stringify(tagNames))
      }
      form.set('generation_mode', createMode.value === 'ai_parse' ? 'bank_parse' : 'knowledge_generate')
      if (aiProviderConfigId.value) form.set('ai_provider_config_id', aiProviderConfigId.value)
      const typeSettings = serializedQuestionTypeSettings()
      if (!typeSettings) return
      form.set('question_type_settings', typeSettings)
      form.set('question_count_mode', 'adaptive')
      if (extraInstruction.value.trim()) form.set('extra_instruction', extraInstruction.value.trim())
      form.set('inherit_context', String(isExtend.value ? inheritContext.value : false))
      form.set('include_existing_questions', String(isExtend.value ? includeExistingQuestions.value : false))
      form.set('generate_description', String(generateDescription.value))
      const data = isExtend.value && extendBankId.value
        ? await extendWorkflow(extendBankId.value, form)
        : await createWorkflow(form)
      toast.show(`已创建${isExtend.value ? '扩展' : '生成'}工作流 #${data.workflow_id}`, 'success')
      await complete('bank-generate-submitted', data)
    }
    reset()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '提交失败', 'error')
  } finally {
    submitting.value = false
  }
}

watch(createMode, () => {
  uploadRef.value?.clearFiles()
  files.value = []
})

load()
</script>

<template>
  <section v-loading="loading" class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">{{ isExtend ? `扩展题库${bank ? '：' + bank.title : ''}` : '新建题库' }}</h1>
        <p class="mt-1 text-sm text-slate-500">{{ isExtend ? '从文件继续为当前题库补充题目。' : '从知识库、已有题库文档或 JSON 文件创建题库。' }}</p>
      </div>

      <el-form label-position="top">
        <el-form-item label="创建方式">
          <el-radio-group v-model="createMode">
            <el-radio-button value="ai_knowledge">从知识库生成</el-radio-button>
            <el-radio-button value="ai_parse">从题库解析</el-radio-button>
            <el-radio-button value="json_import">导入 JSON</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <template v-if="showNewBankFields">
          <el-form-item label="题库名称"><el-input v-model="title" placeholder="输入题库名称" /></el-form-item>
          <el-form-item label="描述"><el-input v-model="description" type="textarea" :rows="2" placeholder="简短描述（可选）" /></el-form-item>
          <el-form-item label="标签">
            <el-select v-model="selectedTags" multiple filterable allow-create default-first-option clearable placeholder="添加标签" style="width: 100%">
              <el-option v-for="(tag, index) in selectedTags" :key="tagKey(tag, index)" :label="tagLabel(tag)" :value="tag" />
            </el-select>
          </el-form-item>
        </template>

        <template v-if="createMode !== 'json_import'">
          <el-form-item label="AI 模型">
            <el-select v-model="aiProviderConfigId" class="w-full">
              <el-option v-for="config in configs" :key="config.id" :value="String(config.id)" :label="configLabel(config)" />
            </el-select>
          </el-form-item>
          <el-form-item label="题型配置">
            <div class="w-full overflow-hidden rounded-lg border border-slate-200">
              <div v-for="row in questionTypeRows" :key="row.key" class="grid grid-cols-[96px_1fr_140px] items-center gap-3 border-b border-slate-100 px-3 py-2 last:border-b-0">
                <el-checkbox v-model="questionTypeSettings[row.key].enabled">{{ row.label }}</el-checkbox>
                <el-checkbox v-if="createMode === 'ai_knowledge'" v-model="questionTypeSettings[row.key].useCount" :disabled="!questionTypeSettings[row.key].enabled">限定数量</el-checkbox>
                <span v-else class="text-xs text-slate-500">解析该题型</span>
                <el-input-number v-if="createMode === 'ai_knowledge'" v-model="questionTypeSettings[row.key].count" size="small" :min="1" :max="100" :disabled="!questionTypeSettings[row.key].enabled || !questionTypeSettings[row.key].useCount" />
              </div>
            </div>
            <p v-if="createMode === 'ai_knowledge'" class="mt-2 text-xs text-slate-500">不勾选限定数量表示该题型由 AI 自适应；不生成某题型请取消左侧勾选。</p>
          </el-form-item>
          <el-form-item label="额外指令（可选）">
            <el-input v-model="extraInstruction" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="例如：题目偏实战场景；解析更详细" />
          </el-form-item>
          <el-form-item v-if="createMode === 'ai_knowledge'"><el-checkbox v-model="generateDescription">AI 自动生成描述</el-checkbox></el-form-item>
          <el-form-item v-if="isExtend"><el-checkbox v-model="inheritContext">使用已有 AI 描述</el-checkbox></el-form-item>
          <el-form-item v-if="isExtend"><el-checkbox v-model="includeExistingQuestions">发送已有题目给 AI 参考</el-checkbox></el-form-item>
        </template>

        <el-form-item label="上传文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="createMode === 'json_import' ? 1 : 20"
            :multiple="createMode !== 'json_import'"
            :accept="createMode === 'json_import' ? '.json' : '.txt,.docx,.pdf'"
            :on-change="onUploadChange"
            :on-remove="onUploadRemove"
          >
            <el-button>选择文件</el-button>
            <template #tip><span class="ml-2 text-sm text-slate-500">{{ createMode === 'json_import' ? '仅支持 .json，一次一个文件' : '支持 .txt / .docx / .pdf，可上传多个文件' }}</span></template>
          </el-upload>
        </el-form-item>
      </el-form>

      <div class="flex justify-end gap-2 pt-2">
        <RouterLink v-if="createMode !== 'json_import' && !configs.length" to="/settings/ai-providers"><el-button>先配置 AI</el-button></RouterLink>
        <el-button @click="closeWindow">取消</el-button>
        <el-button v-if="createMode === 'json_import' || configs.length" type="primary" :loading="submitting" @click="submit">
          {{ createMode === 'json_import' ? '开始导入' : '开始生成' }}
        </el-button>
      </div>
    </div>
  </section>
</template>
