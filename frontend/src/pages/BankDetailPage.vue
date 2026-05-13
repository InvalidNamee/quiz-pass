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
  <section v-if="bank" class="grid gap-5">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-2xl font-bold">{{ bank.title }}</h1>
            <span class="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{{ bank.visibility === 'public' ? '公开' : '私有' }}</span>
            <span class="rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700">{{ bank.generation_status }}</span>
          </div>
          <p class="mt-3 max-w-3xl text-slate-600">{{ bank.description || '暂无描述' }}</p>
          <RouterLink class="mt-4 flex w-fit items-center gap-2 text-sm text-slate-600 hover:text-blue-700" :to="`/users/${bank.owner_id}`">
            <img v-if="bank.owner_avatar_url" class="h-9 w-9 rounded-full object-cover" :src="bank.owner_avatar_url" alt="" />
            <span v-else class="grid h-9 w-9 place-items-center rounded-full bg-slate-800 text-xs font-bold text-white">{{ (bank.owner_display_name || bank.owner_username || 'U').slice(0, 1).toUpperCase() }}</span>
            <span>作者 {{ bank.owner_display_name || bank.owner_username || `#${bank.owner_id}` }}</span>
          </RouterLink>
        </div>
        <button class="rounded-md bg-slate-100 px-4 py-2 text-slate-700 hover:bg-slate-200" @click="favorite">{{ bank.is_favorited ? '取消收藏' : '收藏题库' }}</button>
      </div>
      <div class="mt-5 grid gap-3 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-lg bg-slate-50 p-3"><span class="block text-xs text-slate-500">题目数</span><strong>{{ bank.question_count }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="block text-xs text-slate-500">收藏数</span><strong>{{ bank.favorite_count }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="block text-xs text-slate-500">生成状态</span><strong>{{ bank.generation_status }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="block text-xs text-slate-500">模型</span><strong>{{ bank.ai_model_name || '手动维护' }}</strong></div>
      </div>
    </div>

    <div class="grid gap-3 rounded-xl border border-slate-200 bg-white p-5">
      <h2 class="text-lg font-semibold">练习与内容</h2>
      <div class="flex flex-wrap gap-2">
        <RouterLink class="rounded-md bg-blue-600 px-4 py-2 text-white" :to="`/banks/${bank.id}/practice/setup`">开始练习</RouterLink>
        <RouterLink class="rounded-md bg-slate-100 px-4 py-2 text-slate-700" :to="`/banks/${bank.id}/mistakes`">错题</RouterLink>
        <RouterLink class="rounded-md bg-slate-100 px-4 py-2 text-slate-700" :to="`/banks/${bank.id}/questions`">题目管理</RouterLink>
        <RouterLink class="rounded-md bg-slate-100 px-4 py-2 text-slate-700" :to="`/banks/${bank.id}/import`">导入导出</RouterLink>
      </div>
    </div>

    <div v-if="auth.user?.id === bank.owner_id" class="grid gap-3 rounded-xl border border-slate-200 bg-white p-5">
      <h2 class="text-lg font-semibold">题库管理</h2>
      <div class="flex flex-wrap gap-2">
        <button class="rounded-md bg-slate-100 px-4 py-2 text-slate-700" @click="editing = !editing">{{ editing ? '收起编辑' : '编辑题库' }}</button>
        <button class="rounded-md bg-red-50 px-4 py-2 text-red-700" @click="removeBank">删除题库</button>
      </div>
    </div>

    <div v-if="editing" class="grid gap-3 rounded-xl border border-slate-200 bg-white p-6">
      <input v-model="editForm.title" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题库名称" />
      <textarea v-model="editForm.description" class="min-h-28 rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题库描述" />
      <select v-model="editForm.visibility" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="private">私有</option>
        <option value="public">公开</option>
      </select>
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="saveEdit">保存题库</button>
    </div>
  </section>
</template>
