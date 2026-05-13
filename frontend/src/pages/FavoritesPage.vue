<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Page, type QuestionBank } from '../api/client'

const banks = ref<QuestionBank[]>([])

async function load() {
  banks.value = (await api<Page<QuestionBank>>('/api/v1/question-banks/favorites')).items
}

onMounted(load)
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">我的收藏</h1>
    <div class="mt-4 grid gap-3">
      <RouterLink v-for="bank in banks" :key="bank.id" class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" :to="`/banks/${bank.id}`">
        <div>
          <strong>{{ bank.title }}</strong>
          <span class="block text-sm text-slate-500">作者 {{ bank.owner_display_name || bank.owner_username }} · {{ bank.question_count }} 题 · {{ bank.favorite_count }} 收藏</span>
        </div>
      </RouterLink>
    </div>
  </section>
</template>
