<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Page, type QuestionBank } from '../api/client'

const banks = ref<QuestionBank[]>([])

async function load() {
  const data = await api<Page<QuestionBank>>('/api/v1/question-banks/public')
  banks.value = data.items
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
    <div class="mt-4 grid gap-3">
      <article v-for="bank in banks" :key="bank.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <RouterLink :to="`/banks/${bank.id}`">
          <strong>{{ bank.title }}</strong>
          <span class="block text-sm text-slate-500">作者 {{ bank.owner_display_name || bank.owner_username }} · {{ bank.question_count }} 题 · {{ bank.favorite_count }} 收藏</span>
        </RouterLink>
        <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="toggleFavorite(bank)">{{ bank.is_favorited ? '取消收藏' : '收藏' }}</button>
      </article>
    </div>
  </section>
</template>
