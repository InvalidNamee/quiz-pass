<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, type Page, type Question } from '../api/client'

const route = useRoute()
const bankId = Number(route.params.bankId)
const questions = ref<Question[]>([])
const keyword = ref('')
const form = reactive({
  type: 'single',
  stem: '',
  explanation: '',
  options: [
    { label: 'A', content: '', is_correct: true },
    { label: 'B', content: '', is_correct: false },
    { label: 'C', content: '', is_correct: false },
    { label: 'D', content: '', is_correct: false },
  ],
})

async function load() {
  const q = keyword.value ? `?keyword=${encodeURIComponent(keyword.value)}` : ''
  const data = await api<Page<Question>>(`/api/v1/question-banks/${bankId}/questions${q}`)
  questions.value = data.items
}

async function createQuestion() {
  await api<Question>(`/api/v1/question-banks/${bankId}/questions`, { method: 'POST', body: JSON.stringify(form) })
  form.stem = ''
  form.explanation = ''
  form.options.forEach((option, index) => {
    option.content = ''
    option.is_correct = index === 0
  })
  await load()
}

async function removeQuestion(id: number) {
  await api(`/api/v1/questions/${id}`, { method: 'DELETE' })
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-bold">题目管理</h1>
      <RouterLink class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" :to="`/banks/${bankId}`">返回题库</RouterLink>
    </div>
    <div class="my-4 grid max-w-2xl gap-3 sm:grid-cols-[1fr_auto]">
      <input v-model="keyword" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="搜索题干" @keyup.enter="load" />
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="load">搜索</button>
    </div>
    <div class="my-4 grid max-w-3xl gap-3">
      <select v-model="form.type" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="single">单选</option>
        <option value="multiple">多选</option>
      </select>
      <textarea v-model="form.stem" class="min-h-28 rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题干" />
      <div v-for="option in form.options" :key="option.label" class="grid gap-2 sm:grid-cols-[64px_1fr_100px]">
        <input v-model="option.label" class="rounded-md border border-slate-300 bg-white px-3 py-2" />
        <input v-model="option.content" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="选项内容" />
        <label class="flex items-center gap-2"><input v-model="option.is_correct" type="checkbox" /> 正确</label>
      </div>
      <textarea v-model="form.explanation" class="min-h-28 rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="解析" />
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="createQuestion">添加题目</button>
    </div>
    <div class="mt-4 grid gap-3">
      <article v-for="question in questions" :key="question.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div>
          <strong>{{ question.stem }}</strong>
          <span class="block text-sm text-slate-500">{{ question.type }} · {{ question.source }} · {{ question.options.length }} 个选项</span>
        </div>
        <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="removeQuestion(question.id)">删除</button>
      </article>
    </div>
  </section>
</template>
