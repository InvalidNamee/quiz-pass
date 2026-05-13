<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, type QuestionBank, type UserPublic } from '../api/client'
import AppAvatar from '../components/AppAvatar.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'

const route = useRoute()
const user = ref<UserPublic | null>(null)
const banks = ref<QuestionBank[]>([])
const loading = ref(true)

function formatDate(value: string) {
  return new Date(value).toLocaleDateString()
}

onMounted(async () => {
  try {
    user.value = await api<UserPublic>(`/api/v1/users/${route.params.userId}`)
    banks.value = await api<QuestionBank[]>(`/api/v1/users/${route.params.userId}/public-question-banks`)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section v-if="loading">
    <AppLoading />
  </section>

  <section v-else-if="user" class="grid gap-6">
    <div class="page-card p-6">
      <div class="flex flex-wrap items-center gap-4">
        <AppAvatar :src="user.avatar_url" :username="user.display_name || user.username" size="lg" />
        <div class="min-w-0">
          <h1 class="text-2xl font-bold">{{ user.display_name || user.username }}</h1>
          <p class="text-slate-500">@{{ user.username }} · #{{ user.id }}</p>
        </div>
      </div>
      <p class="mt-4 text-slate-700">{{ user.bio || '这个用户还没有填写简介。' }}</p>
      <div class="mt-5 grid gap-3 text-sm sm:grid-cols-3">
        <div class="rounded-lg bg-slate-50 p-3">
          <span class="text-slate-500">公开题库</span>
          <strong class="block text-slate-900">{{ user.public_bank_count }}</strong>
        </div>
        <div class="rounded-lg bg-slate-50 p-3">
          <span class="text-slate-500">注册时间</span>
          <strong class="block text-slate-900">{{ formatDate(user.created_at) }}</strong>
        </div>
        <div class="rounded-lg bg-slate-50 p-3">
          <span class="text-slate-500">用户 ID</span>
          <strong class="block text-slate-900">#{{ user.id }}</strong>
        </div>
      </div>
    </div>

    <div>
      <div class="flex items-center justify-between gap-4 mb-4">
        <h2 class="text-xl font-semibold">公开题库</h2>
        <span class="text-sm text-slate-500">{{ banks.length }} 个可见</span>
      </div>

      <AppEmpty v-if="!banks.length" title="暂无公开题库" />

      <div v-else class="grid gap-3">
        <RouterLink v-for="bank in banks" :key="bank.id" class="page-card flex items-center justify-between gap-4 p-4 hover:border-brand-500/30" :to="`/banks/${bank.id}`">
          <div class="min-w-0">
            <strong class="block truncate">{{ bank.title }}</strong>
            <span class="text-sm text-slate-500">{{ bank.description || '暂无描述' }}</span>
          </div>
          <span class="shrink-0 text-sm text-slate-500">{{ bank.question_count }} 题 · {{ bank.favorite_count }} 收藏</span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
