<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api, type QuestionBank } from '../api/client'

const router = useRouter()
const file = ref<File | null>(null)
const visibility = ref('private')
const error = ref('')
const submitting = ref(false)

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
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
    form.set('visibility', visibility.value)
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
  <section class="mx-auto grid max-w-3xl gap-5">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h1 class="text-2xl font-bold">导入题库</h1>
      <p class="mt-2 text-slate-600">从符合导出格式的 JSON 文件直接创建一个新题库。</p>
    </div>

    <div class="grid gap-4 rounded-xl border border-slate-200 bg-white p-6">
      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">JSON 文件</span>
        <input class="rounded-md border border-slate-300 bg-white px-3 py-2" type="file" accept=".json,application/json" @change="onFile" />
      </label>
      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">导入后可见性</span>
        <select v-model="visibility" class="rounded-md border border-slate-300 bg-white px-3 py-2">
          <option value="private">私有</option>
          <option value="public">公开</option>
        </select>
      </label>
      <div class="flex flex-wrap gap-2">
        <button class="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50" :disabled="submitting" @click="submit">
          {{ submitting ? '导入中' : '开始导入' }}
        </button>
        <RouterLink class="rounded-md bg-slate-100 px-4 py-2 text-slate-700" to="/banks">返回我的题库</RouterLink>
      </div>
      <p v-if="error" class="text-sm font-medium text-red-700">{{ error }}</p>
    </div>
  </section>
</template>
