<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { QuestionBankV2 } from '../api/types'
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
const useLimit = ref(false)
const limit = ref(20)
const loading = ref(false)
const starting = ref(false)

const visible = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const modeDescriptions: Record<string, string> = {
  practice: '答完即出结果和解析，适合日常练习。',
  exam: '模拟真实考试，交卷后统一阅卷出分。',
  mistake_review: '只练习当前题库中做错的题目，查漏补缺。',
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
    if (useLimit.value) body.question_limit = limit.value
    const session = await createSession(body as { bank_id: number; mode: string; question_limit?: number })
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
        <el-form-item><el-checkbox v-model="useLimit">指定题数</el-checkbox></el-form-item>
        <el-form-item v-if="useLimit" label="题目数量">
          <el-input-number v-model="limit" :min="1" :max="200" />
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="starting" :disabled="!bankId" @click="start">开始</el-button>
    </template>
  </el-dialog>
</template>
