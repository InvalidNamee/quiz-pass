<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Question, QuestionBankV2 } from '../api/types'
import { createQuestion, deleteQuestion, getBank, listQuestions, updateQuestion } from '../api/v2/banks'
import MathText from '../components/MathText.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const bankId = Number(route.params.bankId)
const bank = ref<QuestionBankV2 | null>(null)
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
    bank.value = await getBank(bankId)
    if (!bank.value.permissions.can_manage) {
      toast.show('你没有权限管理这个题库', 'error')
      router.replace(`/banks/${bankId}`)
      return
    }
    const data = await listQuestions(bankId, { keyword: keyword.value.trim() || undefined })
    questions.value = data.items
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '加载题目失败', 'error')
    router.replace(`/banks/${bankId}`)
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
      await updateQuestion(editingQuestion.value.id, { ...form })
      toast.show('题目已更新', 'success')
    } else {
      await createQuestion(bankId, { ...form })
      toast.show('题目已添加', 'success')
    }
    resetForm()
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  }
}

async function removeQuestion(id: number) {
  try {
    await deleteQuestion(id)
    toast.show('已删除', 'info')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '删除失败', 'error')
  }
}

onMounted(load)
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <h1 class="qp-title">题目管理</h1>
      <RouterLink :to="`/banks/${bankId}`"><el-button size="small">返回题库</el-button></RouterLink>
    </div>

    <div class="grid gap-3 lg:grid-cols-[minmax(0,1fr)_400px]">
      <div class="grid gap-3">
        <div class="qp-toolbar">
          <el-input v-model="keyword" size="small" placeholder="搜索题干" clearable class="!w-64" @input="onKeywordInput" @keyup.enter="load" />
        </div>

        <el-table v-loading="loading" :data="questions" size="small" empty-text="暂无题目">
          <el-table-column label="题目" min-width="320">
            <template #default="{ row }: { row: Question }">
              <div class="min-w-0">
                <div class="flex items-start gap-2">
                  <el-tag :type="row.type === 'single' ? 'primary' : 'warning'" size="small">{{ row.type === 'single' ? '单选' : '多选' }}</el-tag>
                  <MathText as="strong" class="line-clamp-2 text-slate-900" :text="row.stem" />
                </div>
                <MathText v-if="row.explanation" as="p" class="mt-1 line-clamp-1 text-sm text-slate-500" :text="row.explanation" />
              </div>
            </template>
          </el-table-column>
          <el-table-column label="选项" width="70" align="center">
            <template #default="{ row }: { row: Question }">{{ row.options.length }}</template>
          </el-table-column>
          <el-table-column label="来源" width="100">
            <template #default="{ row }: { row: Question }">{{ row.source }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }: { row: Question }">
              <el-button text size="small" @click="editQuestion(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="removeQuestion(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-form class="qp-section self-start" label-position="top">
        <h2 class="qp-section-title">{{ editingQuestion ? '编辑题目' : '添加题目' }}</h2>

        <el-form-item label="题型">
          <el-select v-model="form.type" @change="form.options.forEach(o => o.is_correct = false); form.options[0].is_correct = true">
            <el-option value="single" label="单选" />
            <el-option value="multiple" label="多选" />
          </el-select>
        </el-form-item>

        <el-form-item label="题干">
          <el-input v-model="form.stem" type="textarea" :rows="3" placeholder="题目内容" />
        </el-form-item>

        <div class="grid gap-2">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-slate-700">选项</span>
            <el-button text size="small" @click="addOption">添加选项</el-button>
          </div>
          <div v-for="(option, index) in form.options" :key="index" class="flex items-center gap-2">
            <span class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-bold text-slate-600">{{ option.label }}</span>
            <el-input v-model="option.content" :placeholder="`选项 ${option.label}`" size="small" />
            <el-button size="small" :type="option.is_correct ? 'success' : 'default'" @click="toggleCorrect(index)">{{ option.is_correct ? '正确' : '设为正确' }}</el-button>
            <el-button v-if="form.options.length > 2" size="small" type="danger" text @click="removeOption(index)">删除</el-button>
          </div>
        </div>

        <el-form-item label="解析（可选）">
          <el-input v-model="form.explanation" type="textarea" :rows="3" placeholder="答案解析" />
        </el-form-item>

        <div class="flex gap-2">
          <el-button type="primary" @click="saveQuestion">{{ editingQuestion ? '更新题目' : '添加题目' }}</el-button>
          <el-button v-if="editingQuestion" @click="resetForm">取消编辑</el-button>
        </div>
      </el-form>
    </div>
  </section>
</template>
