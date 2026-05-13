<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type QuestionBank } from '../api/client'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const bank = ref<QuestionBank | null>(null)
const editing = ref(false)
const editForm = ref({ title: '', description: '', visibility: 'private' })

async function load() {
  bank.value = await api<QuestionBank>(`/api/v1/question-banks/${route.params.bankId}`)
  editForm.value = {
    title: bank.value.title,
    description: bank.value.description || '',
    visibility: bank.value.visibility,
  }
}

async function favorite() {
  if (!bank.value) return
  await api(`/api/v1/question-banks/${bank.value.id}/favorite`, { method: bank.value.is_favorited ? 'DELETE' : 'POST' })
  await load()
}

async function saveEdit() {
  if (!bank.value) return
  await api<QuestionBank>(`/api/v1/question-banks/${bank.value.id}`, {
    method: 'PATCH',
    body: JSON.stringify(editForm.value),
  })
  editing.value = false
  await load()
}

async function removeBank() {
  if (!bank.value || !confirm('确定删除这个题库吗？')) return
  await api(`/api/v1/question-banks/${bank.value.id}`, { method: 'DELETE' })
  router.push('/banks')
}

onMounted(load)
</script>

<template>
  <section v-if="bank">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold">{{ bank.title }}</h1>
        <p class="mt-1 text-slate-600">{{ bank.description }}</p>
        <RouterLink class="text-blue-700" :to="`/users/${bank.owner_id}`">作者：{{ bank.owner_display_name || bank.owner_username || `#${bank.owner_id}` }}</RouterLink>
      </div>
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="favorite">{{ bank.is_favorited ? '取消收藏' : '收藏' }}</button>
    </div>
    <div class="mt-3 flex flex-wrap gap-3 text-sm text-slate-500">
      <span>{{ bank.visibility }}</span>
      <span>{{ bank.generation_status }}</span>
      <span>{{ bank.question_count }} 题</span>
      <span>{{ bank.favorite_count }} 收藏</span>
      <span v-if="bank.ai_model_name">{{ bank.ai_model_name }}</span>
    </div>
    <div class="mt-5 flex flex-wrap gap-2">
      <RouterLink class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" :to="`/banks/${bank.id}/questions`">题目管理</RouterLink>
      <RouterLink class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" :to="`/banks/${bank.id}/import`">导入导出</RouterLink>
      <RouterLink class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" :to="`/banks/${bank.id}/mistakes`">错题</RouterLink>
      <RouterLink class="rounded-md bg-blue-600 px-4 py-2 text-white" :to="`/banks/${bank.id}/practice/setup`">开始练习</RouterLink>
      <button v-if="auth.user?.id === bank.owner_id" class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="editing = !editing">编辑题库</button>
      <button v-if="auth.user?.id === bank.owner_id" class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="removeBank">删除题库</button>
    </div>
    <div v-if="editing" class="my-4 grid max-w-2xl gap-3">
      <input v-model="editForm.title" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题库名称" />
      <textarea v-model="editForm.description" class="min-h-28 rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题库描述" />
      <select v-model="editForm.visibility" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="private">私有</option>
        <option value="public">公开</option>
      </select>
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="saveEdit">保存</button>
    </div>
  </section>
</template>
