<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { MistakeRecord, Page } from '../api/types'
import { createMistakeSession, listMistakes, resolveMistake } from '../api/v2/practice'
import MathText from '../components/MathText.vue'

const route = useRoute()
const router = useRouter()
const bankId = Number(route.params.bankId)
const mistakes = ref<MistakeRecord[]>([])
const pageInfo = ref<Page<MistakeRecord> | null>(null)
const loading = ref(true)
const resolving = ref<Set<number>>(new Set())

async function load(page = 1) {
  loading.value = true
  try {
    const data = await listMistakes(bankId, false, { page })
    mistakes.value = data.items
    pageInfo.value = data
  } finally {
    loading.value = false
  }
}

async function resolve(questionId: number) {
  resolving.value = new Set([...resolving.value, questionId])
  try {
    await resolveMistake(bankId, questionId)
    await load(pageInfo.value?.page || 1)
  } finally {
    const next = new Set(resolving.value)
    next.delete(questionId)
    resolving.value = next
  }
}

async function practice() {
  const session = await createMistakeSession(bankId)
  router.push(`/practice/session/${session.id}`)
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

onMounted(load)
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title">我的错题</h1>
        <p class="qp-subtitle">{{ pageInfo?.total ?? mistakes.length }} 道未掌握</p>
      </div>
      <el-button size="small" :disabled="!mistakes.length" @click="practice">错题练习</el-button>
    </div>

    <el-table v-loading="loading" :data="mistakes" size="small" empty-text="没有错题">
      <el-table-column label="题目" min-width="500">
        <template #default="{ row, $index }">
          <div class="border-l-2 border-l-red-400 pl-3">
            <div class="flex flex-wrap items-center gap-2">
              <el-tag type="danger" size="small">错误 {{ row.wrong_count }} 次</el-tag>
              <el-tag type="warning" size="small">最后错误 {{ formatTime(row.last_wrong_at) }}</el-tag>
              <el-button text size="small" :loading="resolving.has(row.question_id)" @click="resolve(row.question_id)">已掌握</el-button>
            </div>
            <strong class="mt-3 block text-slate-900">
              {{ ((pageInfo?.page || 1) - 1) * (pageInfo?.page_size || mistakes.length) + $index + 1 }}.
              [{{ row.type === 'single' ? '单选' : '多选' }}]
              <MathText class="inline" :text="row.stem" />
            </strong>

            <div class="mt-3 grid gap-1 text-sm text-slate-700">
              <p v-for="option in row.options" :key="option.id" class="m-0 border border-slate-200 bg-white px-3 py-2">
                <span class="font-semibold text-slate-900">{{ option.label }}.</span>
                <MathText class="inline" :text="option.content" />
              </p>
            </div>

            <div class="mt-4 flex flex-wrap gap-3 text-sm">
              <span class="font-medium text-slate-700">正确答案：{{ row.correct_labels.join('、') || '无' }}</span>
              <span class="text-slate-500">题目 #{{ row.question_id }}</span>
            </div>

            <p v-if="row.explanation" class="mt-3 border border-blue-100 bg-blue-50 px-3 py-2 text-sm text-blue-800">
              <MathText :text="row.explanation" />
            </p>
          </div>
        </template>
      </el-table-column>
    </el-table>

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
