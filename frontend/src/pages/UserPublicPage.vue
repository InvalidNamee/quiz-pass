<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, type QuestionBank, type UserPublic } from '../api/client'

const route = useRoute()
const user = ref<UserPublic | null>(null)
const banks = ref<QuestionBank[]>([])

function formatDate(value: string) {
  return new Date(value).toLocaleDateString()
}

onMounted(async () => {
  user.value = await api<UserPublic>(`/api/v1/users/${route.params.userId}`)
  banks.value = await api<QuestionBank[]>(`/api/v1/users/${route.params.userId}/public-question-banks`)
})
</script>

<template>
  <section v-if="user">
    <div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div class="flex flex-wrap items-center gap-4">
        <img v-if="user.avatar_url" class="h-20 w-20 rounded-full object-cover" :src="user.avatar_url" alt="" />
        <span v-else class="grid h-20 w-20 place-items-center rounded-full bg-teal-800 text-2xl font-bold text-white">{{ (user.display_name || user.username).slice(0, 1).toUpperCase() }}</span>
        <div class="min-w-0">
          <h1 class="text-2xl font-bold">{{ user.display_name || user.username }}</h1>
          <p class="text-slate-500">@{{ user.username }} · 用户 #{{ user.id }}</p>
        </div>
      </div>
      <p class="mt-4 text-slate-700">{{ user.bio || '这个用户还没有填写简介。' }}</p>
      <div class="mt-5 grid gap-3 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-3">
        <div class="rounded-md bg-slate-50 p-3">
          <span class="block text-slate-500">公开题库</span>
          <strong class="text-slate-900">{{ user.public_bank_count }}</strong>
        </div>
        <div class="rounded-md bg-slate-50 p-3">
          <span class="block text-slate-500">注册时间</span>
          <strong class="text-slate-900">{{ formatDate(user.created_at) }}</strong>
        </div>
        <div class="rounded-md bg-slate-50 p-3">
          <span class="block text-slate-500">用户 ID</span>
          <strong class="text-slate-900">#{{ user.id }}</strong>
        </div>
      </div>
    </div>
    <div class="mt-6 flex items-center justify-between gap-4">
      <h2 class="text-xl font-semibold">公开题库</h2>
      <span class="text-sm text-slate-500">{{ banks.length }} 个可见</span>
    </div>
    <div class="mt-4 grid gap-3">
      <RouterLink v-for="bank in banks" :key="bank.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-blue-300" :to="`/banks/${bank.id}`">
        <div>
          <strong>{{ bank.title }}</strong>
          <span class="block text-sm text-slate-500">{{ bank.description || '暂无描述' }}</span>
        </div>
        <span class="text-sm text-slate-500">{{ bank.question_count }} 题 · {{ bank.favorite_count }} 收藏</span>
      </RouterLink>
      <div v-if="!banks.length" class="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-center text-slate-500">
        暂无公开题库
      </div>
    </div>
  </section>
</template>
