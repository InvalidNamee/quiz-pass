<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { AIProviderConfig, QuestionBankTag, QuestionBankV2 } from '../api/types'
import { createWorkflow, extendWorkflow } from '../api/v2/aiGeneration'
import { getBank, importJsonNewBank, importJsonToBank } from '../api/v2/banks'
import { listAIConfigs } from '../api/v2/users'
import { useToast } from '../composables/useToast'

type CreateMode = 'ai_knowledge' | 'ai_parse' | 'json_import'
type TagInputValue = QuestionBankTag | string | null | undefined

const props = defineProps<{
  modelValue: boolean
  extendBankId?: number | null
  initialBank?: QuestionBankV2 | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: boolean]; submitted: [] }>()

const router = useRouter()
const toast = useToast()
const title = ref('')
const description = ref('')
const createMode = ref<CreateMode>('ai_knowledge')
const isPublic = ref(false)
const aiProviderConfigId = ref('')
const useQuestionCount = ref(true)
const questionCount = ref(10)
const generateDescription = ref(false)
const extraInstruction = ref('')
const selectedTags = ref<TagInputValue[]>([])
const file = ref<File | null>(null)
const configs = ref<AIProviderConfig[]>([])
const bank = ref<QuestionBankV2 | null>(props.initialBank ?? null)
const submitting = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})
const isExtend = computed(() => Boolean(props.extendBankId))
const showNewBankFields = computed(() => !isExtend.value)

async function load() {
  configs.value = await listAIConfigs()
  const preferred = configs.value.find((item) => item.is_default) ?? configs.value[0]
  if (preferred && !aiProviderConfigId.value) aiProviderConfigId.value = String(preferred.id)
  if (props.extendBankId) {
    bank.value = props.initialBank?.id === props.extendBankId ? props.initialBank : await getBank(props.extendBankId)
  }
}

function reset() {
  title.value = ''
  description.value = ''
  extraInstruction.value = ''
  selectedTags.value = []
  file.value = null
}

function configLabel(config: AIProviderConfig) {
  return config.name ? `${config.name} · ${config.model}` : config.model
}

function fileStem(fileName: string) {
  return fileName.replace(/\.[^/.]+$/, '')
}

function normalizeTagNames(values: TagInputValue[] = selectedTags.value) {
  const seen = new Set<string>()
  const names: string[] = []
  values.forEach((value) => {
    const rawName = typeof value === 'string' ? value : value?.name
    const name = (rawName || '').trim()
    if (!name || name.toLowerCase() === 'none' || seen.has(name)) return
    seen.add(name)
    names.push(name)
  })
  return names
}

function tagKey(tag: TagInputValue, index: number) {
  if (typeof tag === 'string') return tag
  return tag?.id || tag?.name || index
}

function tagLabel(tag: TagInputValue) {
  return typeof tag === 'string' ? tag : tag?.name || ''
}

async function prefillFromJson(uploadedFile: File) {
  if (isExtend.value || createMode.value !== 'json_import') return
  try {
    const payload = JSON.parse(await uploadedFile.text())
    const bankInfo = payload?.bank && typeof payload.bank === 'object' ? payload.bank : {}
    if (typeof bankInfo.title === 'string' && bankInfo.title.trim()) {
      title.value = bankInfo.title.trim()
    } else if (!title.value.trim()) {
      title.value = fileStem(uploadedFile.name)
    }
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

async function onUploadChange(uploadFile: { raw?: File }) {
  file.value = uploadFile.raw ?? null
  if (!file.value) return
  if (!isExtend.value && !title.value.trim()) title.value = fileStem(file.value.name)
  await prefillFromJson(file.value)
}

function onUploadRemove() {
  file.value = null
}

async function submit() {
  if (!file.value) {
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
    form.set('file', file.value)

    if (createMode.value === 'json_import') {
      form.set('visibility', isPublic.value ? 'public' : 'private')
      const tagNames = normalizeTagNames()
      if (tagNames.length) form.set('tag_names', JSON.stringify(tagNames))
      if (!isExtend.value) form.set('file_stem', fileStem(file.value.name))
      const importedBank = isExtend.value && props.extendBankId
        ? await importJsonToBank(props.extendBankId, form)
        : await importJsonNewBank(form)
      toast.show(`题目已导入「${importedBank.title}」`, 'success')
    } else {
      if (!isExtend.value) {
        form.set('title', title.value)
        if (description.value.trim()) form.set('description', description.value.trim())
        form.set('desired_visibility', isPublic.value ? 'public' : 'private')
        const tagNames = normalizeTagNames()
        if (tagNames.length) form.set('tag_names', JSON.stringify(tagNames))
      }
      form.set('generation_mode', createMode.value === 'ai_parse' ? 'bank_parse' : 'knowledge_generate')
      if (aiProviderConfigId.value) form.set('ai_provider_config_id', aiProviderConfigId.value)
      if (createMode.value === 'ai_knowledge') {
        form.set('question_count_mode', useQuestionCount.value ? 'fixed' : 'adaptive')
        if (useQuestionCount.value) form.set('question_count', String(questionCount.value))
      }
      if (extraInstruction.value.trim()) form.set('extra_instruction', extraInstruction.value.trim())
      form.set('generate_description', String(generateDescription.value))
      const data = isExtend.value && props.extendBankId
        ? await extendWorkflow(props.extendBankId, form)
        : await createWorkflow(form)
      toast.show(`已创建${isExtend.value ? '扩展' : '生成'}工作流 #${data.workflow_id}`, 'success')
    }

    reset()
    visible.value = false
    emit('submitted')
    router.push('/banks/generation-jobs')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '提交失败', 'error')
  } finally {
    submitting.value = false
  }
}

watch(() => props.modelValue, (open) => { if (open) load() }, { immediate: true })
</script>

<template>
  <el-dialog v-model="visible" :title="isExtend ? `扩展题库${bank ? '：' + bank.title : ''}` : '新建题库'" width="760px" top="5vh">
    <el-form label-position="top">
      <el-form-item label="创建方式">
        <el-radio-group v-model="createMode">
          <el-radio-button value="ai_knowledge">从知识库生成</el-radio-button>
          <el-radio-button value="ai_parse">从题库解析</el-radio-button>
          <el-radio-button value="json_import">导入 JSON</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <template v-if="showNewBankFields">
        <div class="grid gap-3 sm:grid-cols-2">
          <el-form-item label="题库名称"><el-input v-model="title" placeholder="起个名字" /></el-form-item>
          <el-form-item label="可见性">
            <el-checkbox v-model="isPublic">{{ createMode === 'json_import' ? '公开题库' : '生成成功后自动公开' }}</el-checkbox>
          </el-form-item>
        </div>
        <el-form-item label="描述"><el-input v-model="description" type="textarea" :rows="2" placeholder="简短描述（可选）" /></el-form-item>
        <el-form-item label="标签">
          <el-select v-model="selectedTags" multiple filterable allow-create default-first-option clearable placeholder="添加标签" style="width: 100%">
            <el-option v-for="(tag, index) in selectedTags" :key="tagKey(tag, index)" :label="tagLabel(tag)" :value="tag" />
          </el-select>
        </el-form-item>
      </template>

      <template v-if="createMode !== 'json_import'">
        <div class="grid gap-3 sm:grid-cols-2">
          <el-form-item label="AI 模型">
            <el-select v-model="aiProviderConfigId" class="w-full">
              <el-option v-for="config in configs" :key="config.id" :value="String(config.id)" :label="configLabel(config)" />
            </el-select>
          </el-form-item>
          <template v-if="createMode === 'ai_knowledge'">
            <el-form-item label="题数">
              <el-checkbox v-model="useQuestionCount">指定题数</el-checkbox>
            </el-form-item>
            <el-form-item v-if="useQuestionCount" label="题目数量">
              <el-input-number v-model="questionCount" :min="1" :max="100" />
            </el-form-item>
          </template>
        </div>
        <el-form-item label="额外指令（可选）">
          <el-input v-model="extraInstruction" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="例如：题目偏实战场景；解析更详细" />
        </el-form-item>
        <el-form-item v-if="createMode === 'ai_knowledge'"><el-checkbox v-model="generateDescription">让 AI 生成题库描述</el-checkbox></el-form-item>
      </template>

      <el-form-item label="上传文件">
        <el-upload
          :auto-upload="false"
          :limit="1"
          :accept="createMode === 'json_import' ? '.json' : '.txt,.docx,.pdf'"
          :on-change="onUploadChange"
          :on-remove="onUploadRemove"
        >
          <el-button>选择文件</el-button>
          <template #tip><span class="ml-2 text-sm text-slate-500">{{ createMode === 'json_import' ? '支持 .json' : '支持 .txt / .docx / .pdf' }}</span></template>
        </el-upload>
      </el-form-item>
    </el-form>
    <template #footer>
      <RouterLink v-if="createMode !== 'json_import' && !configs.length" to="/settings/ai-providers"><el-button>先配置 AI</el-button></RouterLink>
      <el-button @click="visible = false">取消</el-button>
      <el-button v-if="createMode === 'json_import' || configs.length" type="primary" :loading="submitting" @click="submit">
        {{ createMode === 'json_import' ? '开始导入' : '开始生成' }}
      </el-button>
    </template>
  </el-dialog>
</template>
