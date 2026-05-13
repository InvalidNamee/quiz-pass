<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Page, type QuestionBank } from '../api/client'

const banks = ref<QuestionBank[]>([])
const keyword = ref('')
const page = ref(1)
const pageInfo = ref<Page<QuestionBank> | null>(null)

async function load() {
  const params = new URLSearchParams()
  params.set('page', String(page.value))
  if (keyword.value) params.set('keyword', keyword.value)
  const data = await api<Page<QuestionBank>>(`/api/v1/question-banks/public?${params}`)
  pageInfo.value = data
  banks.value = data.items
}

async function search() {
  page.value = 1
  await load()
}

async function goPage(nextPage: number) {
  page.value = nextPage
  await load()
}

async function toggleFavorite(bank: QuestionBank) {
  await api(`/api/v1/question-banks/${bank.id}/favorite`, { method: bank.is_favorited ? 'DELETE' : 'POST' })
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">公开题库</h1>
    <div class="my-4 grid max-w-xl gap-3 sm:grid-cols-[1fr_auto]">
      <input v-model="keyword" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="搜索公开题库" @keyup.enter="search" />
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="search">搜索</button>
    </div>
    <div class="mt-4 grid gap-3">
      <article v-for="bank in banks" :key="bank.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <RouterLink :to="`/banks/${bank.id}`">
          <strong>{{ bank.title }}</strong>
          <span class="block text-sm text-slate-500">作者 {{ bank.owner_display_name || bank.owner_username }} · {{ bank.question_count }} 题 · {{ bank.favorite_count }} 收藏</span>
        </RouterLink>
        <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="toggleFavorite(bank)">{{ bank.is_favorited ? '取消收藏' : '收藏' }}</button>
      </article>
    </div>
    <div v-if="pageInfo" class="mt-4 flex items-center justify-end gap-3 text-sm text-slate-600">
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page <= 1" @click="goPage(pageInfo.page - 1)">上一页</button>
      <span>第 {{ pageInfo.page }} / {{ pageInfo.total_pages || 1 }} 页，共 {{ pageInfo.total }} 个</span>
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page >= pageInfo.total_pages" @click="goPage(pageInfo.page + 1)">下一页</button>
    </div>
  </section>
</template>
