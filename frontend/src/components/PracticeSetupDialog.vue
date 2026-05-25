<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { QuestionBankV2, QuestionType, QuestionTypeSettings } from '../api/types'
import { getBank } from '../api/v2/banks'
import { createSession } from '../api/v2/practice'
import { useToast } from '../composables/useToast'

const props = defineProps<{
  modelValue: boolean
  bankId: number | null
  initialBank?: QuestionBankV2 | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()

const router = useRouter()
const toast = useToast()
const bank = ref<QuestionBankV2 | null>(props.initialBank ?? null)
const mode = ref('practice')
const loading = ref(false)
const starting = ref(false)
const questionTypeRows: Array<{ key: QuestionType; label: string }> = [
  { key: 'single', label: '单选' },
  { key: 'multiple', label: '多选' },
  { key: 'blank', label: '填空' },
  { key: 'short_answer', label: '简答' },
]
const questionTypes = ref<Record<QuestionType, { enabled: boolean; useCount: boolean; count: number }>>({
  short_answer: { enabled: true, useCount: false, count: 1 },
  blank: { enabled: true, useCount: false, count: 5 },
  multiple: { enabled: true, useCount: false, count: 5 },
  single: { enabled: true, useCount: false, count: 10 },
})

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const modeDescriptions: Record<string, string> = {
  practice: '答完即出结果和解析，适合日常练习。',
  exam: '模拟真实考试，交卷后统一阅卷出分。',
  mistake_review: '只练习当前题库中做错的题目，查漏补缺。',
}

function buildQuestionTypeSettings(): QuestionTypeSettings | null {
  const payload = {} as QuestionTypeSettings
  for (const row of questionTypeRows) {
    const config = questionTypes.value[row.key]
    payload[row.key] = {
      enabled: config.enabled,
      count: config.enabled && config.useCount ? config.count : null,
    }
  }
  if (!Object.values(payload).some((item) => item.enabled)) {
    toast.show('至少选择一种题型', 'error')
    return null
  }
  return payload
}

async function load() {
  if (!props.bankId) return
  if (props.initialBank?.id === props.bankId) {
    bank.value = props.initialBank
    return
  }
  loading.value = true
  try {
    bank.value = await getBank(props.bankId)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '加载题库失败', 'error')
  } finally {
    loading.value = false
  }
}

async function start() {
  if (!props.bankId) return
  starting.value = true
  try {
    const body: Record<string, unknown> = { bank_id: props.bankId, mode: mode.value }
    const typeSettings = buildQuestionTypeSettings()
    if (!typeSettings) return
    body.question_type_settings = typeSettings
    const session = await createSession(body as { bank_id: number; mode: string; question_type_settings: QuestionTypeSettings })
    visible.value = false
    router.push(`/practice/session/${session.id}`)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '开始练习失败', 'error')
  } finally {
    starting.value = false
  }
}

watch(() => props.modelValue, (open) => { if (open) load() }, { immediate: true })
</script>

<template>
  <el-dialog v-model="visible" title="开始练习" width="520px">
    <div v-loading="loading">
      <p v-if="bank" class="mb-3 text-sm text-slate-600">{{ bank.title }} · {{ bank.stats.question_count }} 题</p>
      <el-form label-position="top">
        <el-form-item label="练习模式">
          <el-radio-group v-model="mode">
            <el-radio-button value="practice">普通练习</el-radio-button>
            <el-radio-button value="exam">模拟考试</el-radio-button>
            <el-radio-button value="mistake_review">错题复习</el-radio-button>
          </el-radio-group>
          <span class="mt-1 text-sm text-slate-500">{{ modeDescriptions[mode] }}</span>
        </el-form-item>
        <el-form-item label="选择题型与题量">
          <div class="w-full overflow-hidden rounded-lg border border-slate-200">
            <div
              v-for="row in questionTypeRows"
              :key="row.key"
              class="grid grid-cols-[96px_1fr_132px] items-center gap-3 border-b border-slate-100 px-3 py-2 last:border-b-0"
            >
              <el-checkbox v-model="questionTypes[row.key].enabled">{{ row.label }}</el-checkbox>
              <el-checkbox v-model="questionTypes[row.key].useCount" :disabled="!questionTypes[row.key].enabled">限定数量</el-checkbox>
              <el-input-number
                v-model="questionTypes[row.key].count"
                size="small"
                :min="1"
                :max="200"
                :disabled="!questionTypes[row.key].enabled || !questionTypes[row.key].useCount"
              />
            </div>
          </div>
          <p class="mt-2 text-xs text-slate-500">不勾选限定数量表示该题型使用全部可用题；不练某题型请取消左侧勾选。</p>
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="starting" :disabled="!bankId" @click="start">开始</el-button>
    </template>
  </el-dialog>
</template>
