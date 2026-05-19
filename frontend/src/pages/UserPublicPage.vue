<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { QuestionBankV2, UserPublic } from '../api/types'
import { listBanks } from '../api/v2/banks'
import { getUserPublic } from '../api/v2/users'
import AppAvatar from '../components/AppAvatar.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'

const route = useRoute()
const user = ref<UserPublic | null>(null)
const banks = ref<QuestionBankV2[]>([])
const loading = ref(true)

function formatDate(value: string) {
  return new Date(value).toLocaleDateString()
}

onMounted(async () => {
  try {
    const userId = Number(route.params.userId)
    user.value = await getUserPublic(userId)
    banks.value = (await listBanks('public', { owner_id: userId, page_size: 100 })).items
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
    <div>
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

      <div v-else class="divide-y divide-slate-100 border-y border-slate-200">
        <RouterLink v-for="bank in banks" :key="bank.id" class="flex items-center justify-between gap-3 py-2.5" :to="`/banks/${bank.id}`">
          <div class="min-w-0">
            <strong class="block truncate">{{ bank.title }}</strong>
            <span class="text-sm text-slate-500">{{ bank.description || '暂无描述' }}</span>
          </div>
          <span class="shrink-0 text-sm text-slate-500">{{ bank.stats.question_count }} 题 · {{ bank.stats.favorite_count }} 收藏</span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
