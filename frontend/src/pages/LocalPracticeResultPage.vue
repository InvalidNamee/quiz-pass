<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { CircleCheck, CircleX, Lightbulb } from '@lucide/vue'
import { getLocalResult, getLocalSession, syncPendingLocalSessions, typeLabel } from '../local/practice'
import type { LocalPracticeResult, LocalPracticeSession } from '../local/types'
import { useToast } from '../composables/useToast'
import MathText from '../components/MathText.vue'

const route = useRoute()
const toast = useToast()
const sessionId = Number(route.params.localSessionId)
const session = ref<LocalPracticeSession | null>(null)
const results = ref<LocalPracticeResult[]>([])
const loading = ref(false)
const syncing = ref(false)

function isChoice(row: LocalPracticeResult) {
  return row.type === 'single' || row.type === 'multiple'
}

function selectedAnswerText(row: LocalPracticeResult) {
  if (row.is_unanswered) return '未作答'
  if (isChoice(row)) return row.selected_labels.join('、') || '无'
  return row.text_answers.map((answer) => answer || '未填写').join('；') || '无'
}

function correctAnswerText(row: LocalPracticeResult) {
  if (isChoice(row)) return row.correct_labels.join('、') || '无'
  if (row.type === 'blank') return row.correct_text_answers.map((answers, index) => `空 ${index + 1}：${answers.join(' / ')}`).join('；')
  return '见参考给分点'
}

async function load() {
  loading.value = true
  try {
    session.value = await getLocalSession(sessionId)
    results.value = await getLocalResult(sessionId)
  } finally {
    loading.value = false
  }
}

async function syncNow() {
  syncing.value = true
  try {
    const result = await syncPendingLocalSessions()
    toast.show(result.failed.length ? `同步完成，${result.failed.length} 条失败` : '同步完成', result.failed.length ? 'info' : 'success')
    await load()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '同步失败', 'error')
  } finally {
    syncing.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="qp-page space-y-4">
    <div v-if="session" class="qp-section flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="qp-page-title">本地练习报告</h1>
        <p class="qp-page-subtitle">得分 {{ session.score }} · 答对 {{ session.correct_count }} / {{ session.total_questions }} · 同步状态 {{ session.sync_status }}</p>
      </div>
      <div class="flex gap-2">
        <RouterLink to="/local/history"><el-button>本地历史</el-button></RouterLink>
        <el-button type="primary" :loading="syncing" @click="syncNow">同步到服务器</el-button>
      </div>
    </div>

    <div v-loading="loading" class="space-y-3">
      <div
        v-for="(row, index) in results"
        :key="row.question_id"
        class="rounded-lg border bg-white p-4"
        :class="row.is_correct ? 'border-emerald-200' : row.is_unanswered ? 'border-amber-200' : 'border-rose-200'"
      >
        <div class="mb-2 flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-slate-500">#{{ index + 1 }}</span>
            <el-tag size="small" type="info">{{ typeLabel(row.type) }}</el-tag>
          </div>
          <el-tag v-if="row.is_unanswered" type="warning">未作答</el-tag>
          <el-tag v-else-if="row.is_correct" type="success"><CircleCheck :size="12" class="mr-1" />正确</el-tag>
          <el-tag v-else type="danger"><CircleX :size="12" class="mr-1" />错误</el-tag>
        </div>
        <MathText class="text-sm font-semibold text-slate-800" :text="row.stem" />
        <div v-if="row.options.length" class="mt-3 grid gap-1 rounded-md bg-slate-50 p-3 text-sm">
          <div v-for="option in row.options" :key="option.id" class="flex gap-2">
            <span class="font-semibold">{{ option.label }}.</span>
            <MathText :text="option.content" />
          </div>
        </div>
        <div class="mt-3 flex flex-wrap gap-4 text-sm">
          <span>你的答案：{{ selectedAnswerText(row) }}</span>
          <span>参考答案：{{ correctAnswerText(row) }}</span>
        </div>
        <div v-if="row.explanation" class="mt-3 rounded-md border border-indigo-100 bg-indigo-50/40 p-3 text-sm">
          <div class="mb-1 flex items-center gap-1 font-semibold text-indigo-900"><Lightbulb :size="14" />解析</div>
          <MathText :text="row.explanation" />
        </div>
      </div>
    </div>
  </section>
</template>
