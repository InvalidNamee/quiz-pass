<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, type QuestionBank } from '../api/client'

type PublicUser = { id: number; username: string; display_name: string | null; avatar_url: string | null; bio: string | null; public_bank_count: number }
const route = useRoute()
const user = ref<PublicUser | null>(null)
const banks = ref<QuestionBank[]>([])

onMounted(async () => {
  user.value = await api<PublicUser>(`/api/v1/users/${route.params.userId}`)
  banks.value = await api<QuestionBank[]>(`/api/v1/users/${route.params.userId}/public-question-banks`)
})
</script>

<template>
  <section v-if="user">
    <div class="flex items-center gap-3">
      <img v-if="user.avatar_url" class="h-12 w-12 rounded-full object-cover" :src="user.avatar_url" alt="" />
      <span v-else class="grid h-12 w-12 place-items-center rounded-full bg-teal-800 font-bold text-white">{{ (user.display_name || user.username).slice(0, 1).toUpperCase() }}</span>
      <div>
        <h1 class="text-2xl font-bold">{{ user.display_name || user.username }}</h1>
        <p class="text-slate-600">{{ user.bio }}</p>
      </div>
    </div>
    <h2 class="mt-6 text-xl font-semibold">公开题库</h2>
    <div class="mt-4 grid gap-3">
      <RouterLink v-for="bank in banks" :key="bank.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" :to="`/banks/${bank.id}`">
        <strong>{{ bank.title }}</strong>
        <span class="text-sm text-slate-500">{{ bank.question_count }} 题 · {{ bank.favorite_count }} 收藏</span>
      </RouterLink>
    </div>
  </section>
</template>
