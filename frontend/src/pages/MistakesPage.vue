<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MistakeAttempt, Page, QuestionType } from '../api/types'
import { createMistakeSession, listMistakeAttempts, resolveMistakeAttempt } from '../api/v2/practice'
import { CircleX, Zap, CircleCheck, Lightbulb } from '@lucide/vue'
import MathText from '../components/MathText.vue'
import { formatDateTime } from '../utils/dateTime'

const route = useRoute()
const router = useRouter()
const bankId = Number(route.params.bankId)
const mistakes = ref<MistakeAttempt[]>([])
const pageInfo = ref<Page<MistakeAttempt> | null>(null)
const loading = ref(true)
const resolving = ref<Set<number>>(new Set())

async function load(page = 1) {
  loading.value = true
  try {
    const data = await listMistakeAttempts(bankId, false, { page })
    mistakes.value = data.items
    pageInfo.value = data
  } finally {
    loading.value = false
  }
}

async function resolve(attemptId: number) {
  resolving.value = new Set([...resolving.value, attemptId])
  try {
    await resolveMistakeAttempt(bankId, attemptId)
    await load(pageInfo.value?.page || 1)
  } finally {
    const next = new Set(resolving.value)
    next.delete(attemptId)
    resolving.value = next
  }
}

async function practice() {
  const session = await createMistakeSession(bankId)
  router.push(`/practice/session/${session.id}?resume=1`)
}

function formatTime(value: string) {
  return formatDateTime(value)
}

onMounted(load)

const typeLabels: Record<QuestionType, string> = {
  single: '单选',
  multiple: '多选',
  blank: '填空',
  short_answer: '简答',
}

function correctAnswerText(row: MistakeAttempt) {
  if (row.type === 'single' || row.type === 'multiple') return row.correct_labels.join('、') || '无'
  if (row.type === 'blank') {
    return row.correct_text_answers
      .map((answers, index) => `空 ${index + 1}：${answers.join(' / ')}`)
      .join('；') || '无'
  }
  return '见参考给分点'
}

function selectedAnswerText(row: MistakeAttempt) {
  if (row.type === 'single' || row.type === 'multiple') return row.selected_labels.join('、') || '未选择'
  if (row.type === 'blank') {
    return row.text_answers.map((answer, index) => `空 ${index + 1}：${answer || '未填写'}`).join('；') || '未填写'
  }
  return row.text_answers[0] || '未填写'
}
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title flex items-center gap-2"><CircleX :size="20" />我的错题</h1>
        <p class="qp-subtitle">目前共有 {{ pageInfo?.total ?? mistakes.length }} 道错题待订正</p>
      </div>
      <el-tooltip content="错题专项练习" placement="top">
        <el-button
          size="small"
          :disabled="!mistakes.length"
          class="qp-icon-button is-blue"
          @click="practice"
        >
          <Zap :size="16" />
        </el-button>
      </el-tooltip>
    </div>

    <div v-loading="loading" class="grid gap-3">
      <template v-if="mistakes.length">
        <div
          v-for="(row, index) in mistakes"
          :key="row.id"
          class="flex flex-col gap-3 rounded-md border border-l-4 border-slate-200 border-l-rose-400 bg-white p-4"
        >
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div class="flex items-center gap-2">
              <span class="flex h-6 w-6 items-center justify-center rounded-md bg-slate-100 text-xs font-bold text-slate-500">
                {{ ((pageInfo?.page || 1) - 1) * (pageInfo?.page_size || mistakes.length) + index + 1 }}
              </span>
              <el-tag size="small" class="!rounded-md" type="danger">本次错误 #{{ row.id }}</el-tag>
              <el-tag size="small" class="!rounded-md" type="warning">错误时间 {{ formatTime(row.wrong_at) }}</el-tag>
              <el-tag size="small" class="!rounded-md" type="info">来源记录 #{{ row.practice_session_id }}</el-tag>
            </div>

            <el-tooltip content="已订正消灭" placement="top">
              <el-button
                size="small"
                class="qp-icon-button is-green"
                :loading="resolving.has(row.id)"
                @click="resolve(row.id)"
              >
                <CircleCheck :size="16" />
              </el-button>
            </el-tooltip>
          </div>

          <div class="text-sm font-bold text-slate-800 leading-relaxed">
            <el-tag size="small" class="!rounded-md mr-1.5" type="info">{{ typeLabels[row.type] }}</el-tag>
            <MathText :key="`mistake-stem-${row.question_id}`" class="inline" :text="row.stem" />
          </div>

          <div v-if="row.options.length" class="grid gap-2.5">
            <div
              v-for="option in row.options"
              :key="option.id"
              class="flex items-start gap-2.5 rounded-md border border-slate-200 bg-slate-50/40 p-3 text-xs text-slate-600 leading-relaxed"
            >
              <span class="font-extrabold text-slate-700 select-none">{{ option.label }}.</span>
              <MathText :key="`mistake-option-${row.question_id}-${option.id}`" class="inline min-w-0 flex-1" :text="option.content" />
            </div>
          </div>

          <div class="flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-100 px-1 py-1 text-xs font-semibold">
            <div class="flex items-center gap-1.5">
              <span class="text-slate-400">你的选择：</span>
              <span class="text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded font-semibold">
                {{ selectedAnswerText(row) }}
              </span>
            </div>

            <span class="text-slate-300 select-none">/</span>
            <div class="flex items-center gap-1.5">
              <span class="text-slate-400">正确答案：</span>
              <span class="text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded font-mono font-bold tracking-wider">
                {{ correctAnswerText(row) }}
              </span>
            </div>

            <span class="text-slate-300 select-none">/</span>
            <span class="text-slate-400">题目编号：#{{ row.question_id }}</span>
          </div>

          <div
            v-if="row.explanation"
            class="rounded-md border border-indigo-100 bg-indigo-50/40 p-3 text-xs text-indigo-950 leading-relaxed"
          >
            <div class="font-extrabold text-indigo-900 mb-1.5 flex items-center gap-1">
              <span><Lightbulb :size="14" class="mr-1" />题目解析：</span>
            </div>
            <MathText :key="`mistake-explanation-${row.question_id}`" :text="row.explanation" class="text-slate-600" />
          </div>
        </div>
      </template>
      <el-empty v-else description="您非常棒，题库暂无错题记录！" class="rounded-md border border-slate-200 bg-white" />
    </div>

    <el-pagination
      v-if="pageInfo && pageInfo.total_pages > 1"
      background
      size="small"
      :current-page="pageInfo.page"
      :page-count="pageInfo.total_pages"
      :total="pageInfo.total"
      layout="prev, pager, next, total"
      @current-change="load"
    />
  </section>
</template>
