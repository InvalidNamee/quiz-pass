<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, type Page, type Question } from '../api/client'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const toast = useToast()
const bankId = Number(route.params.bankId)
const questions = ref<Question[]>([])
const keyword = ref('')
const loading = ref(true)
const editingQuestion = ref<Question | null>(null)

const form = reactive({
  type: 'single' as 'single' | 'multiple',
  stem: '',
  explanation: '',
  options: [
    { label: 'A', content: '', is_correct: true },
    { label: 'B', content: '', is_correct: false },
  ],
})

function resetForm() {
  form.type = 'single'
  form.stem = ''
  form.explanation = ''
  form.options = [
    { label: 'A', content: '', is_correct: true },
    { label: 'B', content: '', is_correct: false },
  ]
  editingQuestion.value = null
}

function editQuestion(question: Question) {
  editingQuestion.value = question
  form.type = question.type
  form.stem = question.stem
  form.explanation = question.explanation || ''
  form.options = question.options.map(o => ({
    label: o.label,
    content: o.content,
    is_correct: o.is_correct || false,
  }))
}

function addOption() {
  const nextLabel = String.fromCharCode(65 + form.options.length)
  form.options.push({ label: nextLabel, content: '', is_correct: false })
}

function removeOption(index: number) {
  if (form.options.length <= 2) return
  form.options.splice(index, 1)
}

function toggleCorrect(index: number) {
  if (form.type === 'single') {
    form.options.forEach((o, i) => { o.is_correct = i === index })
  } else {
    form.options[index].is_correct = !form.options[index].is_correct
  }
}

async function load() {
  loading.value = true
  try {
    const q = keyword.value ? `?keyword=${encodeURIComponent(keyword.value)}` : ''
    const data = await api<Page<Question>>(`/api/v1/question-banks/${bankId}/questions${q}`)
    questions.value = data.items
  } finally {
    loading.value = false
  }
}

let debounceTimer: ReturnType<typeof setTimeout>
function onKeywordInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(load, 300)
}

async function saveQuestion() {
  if (!form.stem.trim()) {
    toast.show('请输入题干', 'error')
    return
  }
  try {
    if (editingQuestion.value) {
      await api<Question>(`/api/v1/questions/${editingQuestion.value.id}`, { method: 'PATCH', body: JSON.stringify({ ...form }) })
      toast.show('题目已更新', 'success')
    } else {
      await api<Question>(`/api/v1/question-banks/${bankId}/questions`, { method: 'POST', body: JSON.stringify({ ...form }) })
      toast.show('题目已添加', 'success')
    }
    resetForm()
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  }
}

async function removeQuestion(id: number) {
  await api(`/api/v1/questions/${id}`, { method: 'DELETE' })
  toast.show('已删除', 'info')
  await load()
}

onMounted(load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card flex flex-wrap items-center justify-between gap-4 p-6">
      <h1 class="text-2xl font-bold">题目管理</h1>
      <RouterLink :to="`/banks/${bankId}`" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">返回题库</RouterLink>
    </div>

    <div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_400px]">
      <div class="grid gap-5">
        <div class="page-card flex gap-2 p-4">
          <input v-model="keyword" class="flex-1 rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="搜索题干" @input="onKeywordInput" @keyup.enter="load" />
        </div>

        <div v-if="loading">
          <p class="text-sm text-slate-500">加载中…</p>
        </div>

        <div v-else class="grid gap-3">
          <p v-if="!questions.length" class="page-card p-6 text-center text-slate-500">暂无题目</p>
          <article v-for="question in questions" :key="question.id" class="page-card flex items-start justify-between gap-4 p-4">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <strong class="truncate">{{ question.stem }}</strong>
                <AppBadge :variant="question.type === 'single' ? 'info' : 'warning'">{{ question.type === 'single' ? '单选' : '多选' }}</AppBadge>
                <AppBadge variant="default">{{ question.options.length }} 个选项</AppBadge>
              </div>
              <p v-if="question.explanation" class="mt-1 text-sm text-slate-500 truncate">{{ question.explanation }}</p>
            </div>
            <div class="flex shrink-0 gap-2">
              <AppButton variant="ghost" size="sm" @click="editQuestion(question)">编辑</AppButton>
              <AppButton variant="danger" size="sm" @click="removeQuestion(question.id)">删除</AppButton>
            </div>
          </article>
        </div>
      </div>

      <div class="page-card grid gap-3 self-start p-5">
        <h2 class="text-lg font-semibold">{{ editingQuestion ? '编辑题目' : '添加题目' }}</h2>

        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">题型</span>
          <select v-model="form.type" class="rounded-input border border-slate-300 bg-white px-3 py-2" @change="form.options.forEach(o => o.is_correct = false); form.options[0].is_correct = true">
            <option value="single">单选</option>
            <option value="multiple">多选</option>
          </select>
        </label>

        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">题干</span>
          <textarea v-model="form.stem" class="min-h-16 rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="题目内容" />
        </label>

        <div class="grid gap-2">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-slate-700">选项</span>
            <button type="button" class="text-xs text-brand-600 hover:text-brand-700" @click="addOption">+ 添加选项</button>
          </div>
          <div v-for="(option, index) in form.options" :key="index" class="flex items-center gap-2">
            <span class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">{{ option.label }}</span>
            <input v-model="option.content" class="flex-1 rounded-input border border-slate-300 bg-white px-2 py-1.5 text-sm" :placeholder="`选项 ${option.label}`" />
            <button
              type="button"
              :class="[
                'grid h-8 w-8 shrink-0 place-items-center rounded-btn border text-sm font-bold transition-colors',
                option.is_correct ? 'border-green-300 bg-green-50 text-green-700' : 'border-slate-200 text-slate-400 hover:border-slate-300',
              ]"
              @click="toggleCorrect(index)"
            >{{ option.is_correct ? '✓' : '' }}</button>
            <button v-if="form.options.length > 2" type="button" class="grid h-8 w-8 shrink-0 place-items-center rounded-btn text-slate-400 hover:bg-red-50 hover:text-red-500" @click="removeOption(index)">
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>

        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">解析（可选）</span>
          <textarea v-model="form.explanation" class="min-h-16 rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="答案解析" />
        </label>

        <div class="flex gap-2">
          <AppButton @click="saveQuestion">{{ editingQuestion ? '更新题目' : '添加题目' }}</AppButton>
          <AppButton v-if="editingQuestion" variant="ghost" @click="resetForm">取消编辑</AppButton>
        </div>
      </div>
    </div>
  </section>
</template>
