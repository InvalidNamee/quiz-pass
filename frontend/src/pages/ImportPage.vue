<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type QuestionBank } from '../api/client'
import { useAuthStore } from '../stores/auth'
import AppButton from '../components/AppButton.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const bankId = Number(route.params.bankId)
const bank = ref<QuestionBank | null>(null)
const loading = ref(true)
const file = ref<File | null>(null)
const importing = ref(false)
const exporting = ref(false)

async function loadBank() {
  loading.value = true
  try {
    bank.value = await api<QuestionBank>(`/api/v1/question-banks/${bankId}`)
    const canManage = auth.user && (auth.user.id === bank.value.owner_id || auth.user.role === 'admin')
    if (!canManage) {
      router.replace(`/banks/${bankId}`)
      return
    }
  } finally {
    loading.value = false
  }
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function submit() {
  if (!file.value) return
  importing.value = true
  try {
    const form = new FormData()
    form.set('file', file.value)
    const bank = await api<QuestionBank>(`/api/v1/question-banks/${bankId}/import-json`, { method: 'POST', body: form })
    toast.show(`已导入到 ${bank.title}`, 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '导入失败', 'error')
  } finally {
    importing.value = false
  }
}

async function exportJson() {
  exporting.value = true
  try {
    const response = await fetch(`/api/v1/question-banks/${bankId}/export`, {
      headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
    })
    if (!response.ok) throw new Error('导出失败')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `question-bank-${bankId}.json`
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '导出失败', 'error')
  } finally {
    exporting.value = false
  }
}

onMounted(loadBank)
</script>

<template>
  <section v-if="loading" class="mx-auto max-w-2xl">
    <div class="page-card p-6 text-sm text-slate-500">加载中…</div>
  </section>

  <section v-else class="mx-auto grid max-w-2xl gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">导入导出</h1>
      <p class="mt-2 text-slate-600">追加 JSON 题目到当前题库，或导出题库备份。</p>
    </div>
    <div class="page-card grid gap-4 p-6">
      <input class="rounded-input border border-slate-300 bg-white px-3 py-2" type="file" accept=".json" @change="onFile" />
      <div class="flex flex-wrap gap-2">
        <AppButton :loading="importing" @click="submit">导入 JSON</AppButton>
        <AppButton variant="secondary" :loading="exporting" @click="exportJson">导出 JSON</AppButton>
        <AppButton variant="ghost" @click="router.push(`/banks/${bankId}`)">返回题库</AppButton>
      </div>
    </div>
  </section>
</template>
