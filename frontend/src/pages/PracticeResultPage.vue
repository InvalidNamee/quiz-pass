<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { PracticeSession, QuestionType } from '../api/types'
import { getResult, getSession } from '../api/v2/practice'
import { Lightbulb, CircleCheck, CircleX } from '@lucide/vue'
import MathText from '../components/MathText.vue'

type ResultOption = { id: number; label: string; content: string }
type Result = {
  question_id: number
  type: QuestionType
  stem: string
  options: ResultOption[]
  blanks: Array<{ id: number; label: string; sort_order: number }>
  selected_option_ids: number[]
  selected_labels: string[]
  text_answers: string[]
  correct_option_ids: number[]
  correct_labels: string[]
  correct_text_answers: string[][]
  is_correct: boolean
  is_unanswered: boolean
  explanation: string | null
}

const route = useRoute()
const sessionId = Number(route.params.sessionId)
const session = ref<PracticeSession | null>(null)
const results = ref<Result[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    session.value = await getSession(sessionId)
    results.value = await getResult(sessionId)
  } finally {
    loading.value = false
  }
})

const typeLabels: Record<QuestionType, string> = {
  single: '单选题',
  multiple: '多选题',
  blank: '填空题',
  short_answer: '简答题',
}

function isChoice(row: Result) {
  return row.type === 'single' || row.type === 'multiple'
}

function selectedAnswerText(row: Result) {
  if (row.is_unanswered) return '未作答'
  if (isChoice(row)) return row.selected_labels.join('、') || '无'
  return row.text_answers.map((answer) => answer || '未填写').join('；') || '无'
}

function correctAnswerText(row: Result) {
  if (isChoice(row)) return row.correct_labels.join('、') || '无'
  if (row.type === 'blank') {
    return row.correct_text_answers
      .map((answers, index) => `空 ${index + 1}：${answers.join(' / ')}`)
      .join('；') || '无'
  }
  return '见参考给分点'
}
</script>

<template>
  <section class="qp-page space-y-6">
    <!-- Polished Results Header Board -->
    <div v-if="session" class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-500 via-indigo-600 to-purple-600 p-6 text-white shadow-xl shadow-indigo-500/10">
      <div class="absolute -right-10 -bottom-10 h-40 w-40 rounded-full bg-white/10 blur-xl" />
      <div class="relative z-10 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 class="text-2xl font-extrabold tracking-tight">本次练习报告 🎉</h1>
          <p class="mt-1.5 text-xs text-indigo-100">复盘今日错题，查漏补缺，争取下次完美通关！</p>
        </div>
        <div class="flex items-center gap-6">
          <div class="text-center">
            <span class="text-2xl font-black block">{{ session.score }}</span>
            <span class="text-[10px] uppercase font-bold tracking-wider text-indigo-200">得分</span>
          </div>
          <div class="h-8 w-px bg-white/20" />
          <div class="text-center">
            <span class="text-2xl font-black block">{{ session.correct_count }} / {{ session.total_questions }}</span>
            <span class="text-[10px] uppercase font-bold tracking-wider text-indigo-200">答对题数</span>
          </div>
          <div class="h-8 w-px bg-white/20" />
          <div class="text-center">
            <span class="text-2xl font-black block">{{ Math.round((session.correct_count / (session.total_questions || 1)) * 100) }}%</span>
            <span class="text-[10px] uppercase font-bold tracking-wider text-indigo-200">正确率</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading Skeleton or Real Card Stream -->
    <div v-loading="loading" class="space-y-4">
      <template v-if="results.length">
        <div
          v-for="(row, index) in results"
          :key="row.question_id"
          class="relative rounded-2xl border border-slate-100/80 bg-white p-5 shadow-sm transition-all hover:shadow-md flex flex-col gap-3.5"
          :class="{
            'border-l-4 border-l-emerald-500': row.is_correct,
            'border-l-4 border-l-rose-500': !row.is_correct && !row.is_unanswered,
            'border-l-4 border-l-amber-500': row.is_unanswered,
          }"
        >
          <!-- Question Index and Status micro tags -->
          <div class="flex items-center justify-between gap-3 border-b border-slate-50 pb-3">
            <div class="flex min-w-0 items-center gap-2">
              <span class="flex h-6 w-6 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500">
                {{ index + 1 }}
              </span>
              <el-tag size="small" class="!rounded-md" type="info">{{ typeLabels[row.type] }}</el-tag>
            </div>

            <span v-if="row.is_unanswered" class="result-status-pill is-unanswered">未作答</span>
            <span v-else-if="row.is_correct" class="result-status-pill is-correct"><CircleCheck :size="13" />正确</span>
            <span v-else class="result-status-pill is-wrong"><CircleX :size="13" />错误</span>
          </div>

          <!-- Question Stem -->
          <div class="text-sm font-bold text-slate-800 leading-relaxed">
            <MathText :key="`result-stem-${row.question_id}`" class="inline" :text="row.stem" />
          </div>

          <!-- Option lists -->
          <div v-if="row.options.length" class="grid gap-2 bg-slate-50/40 p-3.5 rounded-xl border border-slate-100/50">
            <div
              v-for="option in row.options"
              :key="option.id"
              class="flex items-start gap-2.5 text-xs text-slate-600 leading-relaxed py-1"
            >
              <span class="font-extrabold text-slate-700 select-none">{{ option.label }}.</span>
              <MathText :key="`result-option-${row.question_id}-${option.id}`" class="inline min-w-0 flex-1" :text="option.content" />
            </div>
          </div>

          <!-- Selected & Correct Summary -->
          <div class="flex flex-wrap gap-x-6 gap-y-2 text-xs font-semibold py-1 px-1 border-t border-slate-50 mt-1">
            <div class="flex items-center gap-1.5">
              <span class="text-slate-400">您的答案：</span>
              <span
                v-if="row.is_unanswered"
                class="text-amber-600 bg-amber-50 px-2 py-0.5 rounded font-mono"
              >
                未作答
              </span>
              <span
                v-else
                class="px-2 py-0.5 rounded font-mono"
                :class="row.is_correct ? 'text-emerald-600 bg-emerald-50' : 'text-rose-600 bg-rose-50'"
              >
                {{ selectedAnswerText(row) }}
              </span>
            </div>

            <div class="flex items-center gap-1.5">
              <span class="text-slate-400">{{ row.type === 'short_answer' ? '参考：' : '正确答案：' }}</span>
              <span class="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-mono font-bold tracking-wider">
                {{ correctAnswerText(row) }}
              </span>
            </div>
          </div>

          <!-- Styled explanation section -->
          <div
            v-if="row.explanation"
            class="rounded-xl border border-indigo-50/50 bg-indigo-50/30 p-3.5 text-xs text-indigo-950 leading-relaxed shadow-inner"
          >
            <div class="font-extrabold text-indigo-900 mb-1.5 flex items-center gap-1">
              <span><Lightbulb :size="14" class="mr-1" />题目解析：</span>
            </div>
            <MathText :key="`result-explanation-${row.question_id}`" :text="row.explanation" class="text-slate-600" />
          </div>
        </div>
      </template>
      <el-empty v-else description="暂无练习测试结果" class="bg-white rounded-2xl border border-slate-100 shadow-sm" />
    </div>
  </section>
</template>

<style scoped>
.result-status-pill {
  display: inline-flex;
  width: 64px;
  height: 24px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-radius: 6px;
  border: 1px solid transparent;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.result-status-pill.is-correct {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}

.result-status-pill.is-wrong {
  border-color: #fecaca;
  background: #fef2f2;
  color: #b91c1c;
}

.result-status-pill.is-unanswered {
  border-color: #fde68a;
  background: #fffbeb;
  color: #b45309;
}
</style>
