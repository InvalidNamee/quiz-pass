<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MistakeRecord, type Page, type PracticeSession } from '../api/client'
import AppButton from '../components/AppButton.vue'
import AppBadge from '../components/AppBadge.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'
import AppPagination from '../components/AppPagination.vue'
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
    const params = new URLSearchParams({ resolved: 'false', page: String(page) })
    const data = await api<Page<MistakeRecord>>(`/api/v1/question-banks/${bankId}/mistakes?${params}`)
    mistakes.value = data.items
    pageInfo.value = data
  } finally {
    loading.value = false
  }
}

async function resolve(questionId: number) {
  resolving.value = new Set([...resolving.value, questionId])
  try {
    await api(`/api/v1/question-banks/${bankId}/mistakes/${questionId}/resolve`, { method: 'POST' })
    await load(pageInfo.value?.page || 1)
  } finally {
    const next = new Set(resolving.value)
    next.delete(questionId)
    resolving.value = next
  }
}

async function practice() {
  const session = await api<PracticeSession>(`/api/v1/question-banks/${bankId}/mistakes/practice-sessions`, { method: 'POST' })
  router.push(`/practice/session/${session.id}`)
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

onMounted(load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card flex flex-wrap items-center justify-between gap-4 p-6">
      <div>
        <h1 class="text-2xl font-bold">我的错题</h1>
        <p class="mt-1 text-slate-600">我在这个题库下未掌握的错题 {{ pageInfo?.total ?? mistakes.length }} 道</p>
      </div>
      <AppButton :disabled="!mistakes.length" @click="practice">错题练习</AppButton>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!mistakes.length" title="没有错题" description="继续练习，这里只记录你自己在当前题库下做错的题目。" />

    <div v-else class="grid gap-3">
      <article
        v-for="(item, index) in mistakes"
        :key="item.id"
        class="page-card border-l-4 border-l-red-300 bg-red-50/20 p-5"
      >
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <AppBadge variant="danger">错误 {{ item.wrong_count }} 次</AppBadge>
              <AppBadge variant="warning">最后错误 {{ formatTime(item.last_wrong_at) }}</AppBadge>
            </div>
            <strong class="mt-3 block text-slate-900">
              {{ ((pageInfo?.page || 1) - 1) * (pageInfo?.page_size || mistakes.length) + index + 1 }}.
              [{{ item.type === 'single' ? '单选' : '多选' }}]
              <MathText class="inline" :text="item.stem" />
            </strong>
          </div>
          <AppButton variant="ghost" size="sm" :loading="resolving.has(item.question_id)" @click="resolve(item.question_id)">已掌握</AppButton>
        </div>

        <div class="mt-4 grid gap-2 text-sm text-slate-700">
          <p v-for="option in item.options" :key="option.id" class="m-0 rounded-lg bg-white px-3 py-2 ring-1 ring-slate-200">
            <span class="font-semibold text-slate-900">{{ option.label }}.</span>
            <MathText class="inline" :text="option.content" />
          </p>
        </div>

        <div class="mt-4 flex flex-wrap gap-3 text-sm">
          <span class="font-medium text-slate-700">正确答案：{{ item.correct_labels.join('、') || '无' }}</span>
          <span class="text-slate-500">题目 #{{ item.question_id }}</span>
        </div>

        <p v-if="item.explanation" class="mt-3 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">
          <MathText :text="item.explanation" />
        </p>
      </article>

      <AppPagination
        v-if="pageInfo && pageInfo.total_pages > 1"
        :page="pageInfo.page"
        :total-pages="pageInfo.total_pages"
        :total="pageInfo.total"
        @update:page="load"
      />
    </div>
  </section>
</template>
