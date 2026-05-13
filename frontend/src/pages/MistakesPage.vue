<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MistakeRecord, type Page, type PracticeSession } from '../api/client'
import AppButton from '../components/AppButton.vue'
import AppBadge from '../components/AppBadge.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'

const route = useRoute()
const router = useRouter()
const bankId = Number(route.params.bankId)
const mistakes = ref<MistakeRecord[]>([])
const loading = ref(true)
const resolving = ref<Set<number>>(new Set())

async function load() {
  loading.value = true
  try {
    const data = await api<Page<MistakeRecord>>(`/api/v1/question-banks/${bankId}/mistakes?resolved=false`)
    mistakes.value = data.items
  } finally {
    loading.value = false
  }
}

async function resolve(questionId: number) {
  resolving.value.add(questionId)
  await api(`/api/v1/question-banks/${bankId}/mistakes/${questionId}/resolve`, { method: 'POST' })
  resolving.value.delete(questionId)
  await load()
}

async function practice() {
  const session = await api<PracticeSession>(`/api/v1/question-banks/${bankId}/mistakes/practice-sessions`, { method: 'POST' })
  router.push(`/practice/session/${session.id}`)
}

onMounted(load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card flex flex-wrap items-center justify-between gap-4 p-6">
      <div>
        <h1 class="text-2xl font-bold">错题</h1>
        <p class="mt-1 text-slate-600">未掌握的错题 {{ mistakes.length }} 道</p>
      </div>
      <AppButton :disabled="!mistakes.length" @click="practice">错题练习</AppButton>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!mistakes.length" title="没有错题" description="继续练习，这里会记录你做错的题目。" />

    <div v-else class="grid gap-3">
      <article v-for="item in mistakes" :key="item.id" class="page-card flex items-center justify-between gap-4 p-4">
        <div>
          <strong>题目 #{{ item.question_id }}</strong>
          <AppBadge variant="danger" class="ml-2">错误 {{ item.wrong_count }} 次</AppBadge>
        </div>
        <AppButton variant="ghost" size="sm" :loading="resolving.has(item.question_id)" @click="resolve(item.question_id)">已掌握</AppButton>
      </article>
    </div>
  </section>
</template>
