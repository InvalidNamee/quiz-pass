<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { PracticeSession } from '../api/types'
import { getResult, getSession } from '../api/v2/practice'
import MathText from '../components/MathText.vue'

type ResultOption = { id: number; label: string; content: string }
type Result = {
  question_id: number
  type: 'single' | 'multiple'
  stem: string
  options: ResultOption[]
  selected_option_ids: number[]
  selected_labels: string[]
  correct_option_ids: number[]
  correct_labels: string[]
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
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <div>
      <h1 class="qp-title">练习结果</h1>
      <p v-if="session" class="qp-subtitle">
        得分 <strong class="text-slate-900">{{ session.score }}</strong>，答对 {{ session.correct_count }} / {{ session.total_questions }}
      </p>
      </div>
    </div>

    <el-table v-loading="loading" :data="results" size="small" empty-text="暂无结果">
      <el-table-column label="题目" min-width="500">
        <template #default="{ row, $index }">
          <div
            :class="{
              'border-l-4 border-l-green-500 pl-4': row.is_correct,
              'border-l-4 border-l-red-500 pl-4': !row.is_correct && !row.is_unanswered,
              'border-l-4 border-l-yellow-500 pl-4': row.is_unanswered,
            }"
            class="py-4"
          >
            <div class="flex items-start justify-between gap-2">
              <strong class="text-slate-900">
                {{ $index + 1 }}. [{{ row.type === 'single' ? '单选' : '多选' }}]
                <MathText :key="`result-stem-${row.question_id}`" class="inline" :text="row.stem" />
              </strong>
              <el-tag v-if="row.is_unanswered" type="warning">未作答</el-tag>
              <el-tag v-else-if="row.is_correct" type="success">正确</el-tag>
              <el-tag v-else type="danger">错误</el-tag>
            </div>
            <div class="mt-2 grid gap-1 text-sm text-slate-700">
              <p v-for="option in row.options" :key="option.id" class="m-0">
                <span class="font-medium">{{ option.label }}.</span>
                <MathText :key="`result-option-${row.question_id}-${option.id}`" class="inline" :text="option.content" />
              </p>
            </div>
            <div class="mt-2 flex flex-wrap gap-2 text-sm">
              <span class="text-slate-500">你的选择：{{ row.is_unanswered ? '未作答' : row.selected_labels.join('、') || '无' }}</span>
              <span class="font-medium text-slate-700">正确答案：{{ row.correct_labels.join('、') }}</span>
            </div>
            <p v-if="row.explanation" class="mt-2 border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-800">
              <MathText :key="`result-explanation-${row.question_id}`" :text="row.explanation" />
            </p>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>
