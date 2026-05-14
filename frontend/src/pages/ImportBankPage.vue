<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type QuestionBank, type QuestionBankTag } from '../api/client'
import AppButton from '../components/AppButton.vue'
import BankTagInput from '../components/BankTagInput.vue'

const router = useRouter()
const file = ref<File | null>(null)
const isPublic = ref(false)
const selectedTags = ref<QuestionBankTag[]>([])
const error = ref('')
const submitting = ref(false)

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
  error.value = ''
}

async function submit() {
  if (!file.value) {
    error.value = '请选择 JSON 文件'
    return
  }
  error.value = ''
  submitting.value = true
  try {
    const form = new FormData()
    form.set('file', file.value)
    form.set('visibility', isPublic.value ? 'public' : 'private')
    if (selectedTags.value.length) form.set('tag_names', JSON.stringify(selectedTags.value.map(tag => tag.name)))
    const bank = await api<QuestionBank>('/api/v1/question-banks/import-json', { method: 'POST', body: form })
    router.push(`/banks/${bank.id}`)
  } catch (err) {
    error.value = err instanceof Error ? err.message : '导入失败'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <section class="mx-auto grid max-w-2xl gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">导入题库</h1>
      <p class="mt-2 text-slate-600">从 JSON 文件直接创建新题库。支持 Quiz Pass 导出的格式。</p>
    </div>

    <div class="page-card grid gap-4 p-6">
      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">JSON 文件</span>
        <input class="rounded-input border border-slate-300 bg-white px-3 py-2" type="file" accept=".json,application/json" @change="onFile" />
      </label>
      <label class="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
        <input v-model="isPublic" type="checkbox" class="rounded" /> 公开题库（不勾选则为私有）
      </label>
      <BankTagInput v-model="selectedTags" allow-create label="标签" />
      <p v-if="error" class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      <div class="flex flex-wrap gap-2">
        <AppButton :loading="submitting" @click="submit">开始导入</AppButton>
        <RouterLink to="/banks" class="inline-flex items-center rounded-btn px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">返回我的题库</RouterLink>
      </div>
    </div>
  </section>
</template>
