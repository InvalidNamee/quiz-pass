<script setup lang="ts">
import { computed, ref } from 'vue'
import type { QuestionBankV2, QuestionType, QuestionTypeSettings } from '../../api/types'
import { getBank } from '../../api/v2/banks'
import { createSession } from '../../api/v2/practice'
import { useToast } from '../../composables/useToast'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  bankId?: number
  requestId?: string
}

const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('practice-setup')
const bankId = computed(() => Number(payload.value.bankId))
const bank = ref<QuestionBankV2 | null>(null)
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
const modeDescriptions: Record<string, string> = {
  practice: '答完即出结果和解析，适合日常练习。',
  exam: '模拟真实考试，交卷后统一阅卷出分。',
  mistake_review: '只练习当前题库中做错的题目，查漏补缺。',
}

function buildQuestionTypeSettings(): QuestionTypeSettings | null {
  const result = {} as QuestionTypeSettings
  for (const row of questionTypeRows) {
    const config = questionTypes.value[row.key]
    result[row.key] = {
      enabled: config.enabled,
      count: config.enabled && config.useCount ? config.count : null,
    }
  }
  if (!Object.values(result).some((item) => item.enabled)) {
    toast.show('至少选择一种题型', 'error')
    return null
  }
  return result
}

async function load() {
  if (!bankId.value) return
  loading.value = true
  try {
    bank.value = await getBank(bankId.value)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载题库失败', 'error')
  } finally {
    loading.value = false
  }
}

async function start() {
  if (!bankId.value) return
  const questionTypeSettings = buildQuestionTypeSettings()
  if (!questionTypeSettings) return
  starting.value = true
  try {
    const session = await createSession({ bank_id: bankId.value, mode: mode.value, question_type_settings: questionTypeSettings })
    await complete('practice-created', { sessionId: session.id, bankId: bankId.value })
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '开始练习失败', 'error')
  } finally {
    starting.value = false
  }
}

load()
</script>

<template>
  <section v-loading="loading" class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">开始练习</h1>
        <p class="mt-1 text-sm text-slate-500">{{ bank ? `${bank.title} · ${bank.stats.question_count} 题` : '选择练习模式和题型。' }}</p>
      </div>

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

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">取消</el-button>
        <el-button type="primary" :loading="starting" :disabled="!bankId" @click="start">开始</el-button>
      </div>
    </div>
  </section>
</template>
