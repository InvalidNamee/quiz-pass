<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Page, type QuestionBank } from '../api/client'

const banks = ref<QuestionBank[]>([])
const keyword = ref('')
const visibility = ref('')
const generationStatus = ref('')
const page = ref(1)
const pageInfo = ref<Page<QuestionBank> | null>(null)

async function load() {
  const params = new URLSearchParams()
  params.set('page', String(page.value))
  if (keyword.value) params.set('keyword', keyword.value)
  if (visibility.value) params.set('visibility', visibility.value)
  if (generationStatus.value) params.set('generation_status', generationStatus.value)
  const data = await api<Page<QuestionBank>>(`/api/v1/question-banks?${params}`)
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

async function createBank() {
  const title = prompt('题库名称')
  if (!title) return
  await api<QuestionBank>('/api/v1/question-banks', { method: 'POST', body: JSON.stringify({ title, visibility: 'private' }) })
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-bold">我的题库</h1>
      <button class="rounded-md bg-blue-600 px-4 py-2 text-white" @click="createBank">新建题库</button>
    </div>
    <div class="my-4 grid max-w-3xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <input v-model="keyword" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="搜索题库" @keyup.enter="search" />
      <select v-model="visibility" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="">全部可见性</option>
        <option value="private">私有</option>
        <option value="public">公开</option>
      </select>
      <select v-model="generationStatus" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="">全部生成状态</option>
        <option value="none">普通题库</option>
        <option value="pending">等待生成</option>
        <option value="processing">生成中</option>
        <option value="succeeded">生成成功</option>
        <option value="failed">生成失败</option>
      </select>
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="search">搜索</button>
    </div>
    <div class="mt-4 grid gap-3">
      <RouterLink v-for="bank in banks" :key="bank.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" :to="`/banks/${bank.id}`">
        <strong>{{ bank.title }}</strong>
        <span class="text-sm text-slate-500">作者 {{ bank.owner_display_name || bank.owner_username }} · {{ bank.visibility }} · {{ bank.generation_status }} · {{ bank.question_count }} 题 · {{ bank.favorite_count }} 收藏</span>
      </RouterLink>
    </div>
    <div v-if="pageInfo" class="mt-4 flex items-center justify-end gap-3 text-sm text-slate-600">
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page <= 1" @click="goPage(pageInfo.page - 1)">上一页</button>
      <span>第 {{ pageInfo.page }} / {{ pageInfo.total_pages || 1 }} 页，共 {{ pageInfo.total }} 个</span>
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page >= pageInfo.total_pages" @click="goPage(pageInfo.page + 1)">下一页</button>
    </div>
  </section>
</template>
