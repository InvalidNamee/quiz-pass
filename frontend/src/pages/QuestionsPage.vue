<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
const drawerOpen = ref(false)

type QuestionForm = {
  type: 'single' | 'multiple'
  stem: string
  explanation: string
  options: Array<{ label: string; content: string; is_correct: boolean }>
}

const form = ref<QuestionForm>({
  type: 'single' as 'single' | 'multiple',
  stem: '',
  explanation: '',
  options: [
    { label: 'A', content: '', is_correct: true },
    { label: 'B', content: '', is_correct: false },
  ],
})
const drawerTitle = computed(() => editingQuestion.value ? '编辑题目' : '添加题目')

function emptyForm(): QuestionForm {
  return {
    type: 'single',
    stem: '',
    explanation: '',
    options: [
      { label: 'A', content: '', is_correct: true },
      { label: 'B', content: '', is_correct: false },
    ],
  }
}

function resetForm() {
  form.value = emptyForm()
  editingQuestion.value = null
  drawerOpen.value = false
}

function openCreate() {
  editingQuestion.value = null
  form.value = emptyForm()
  drawerOpen.value = true
}

function editQuestion(question: Question) {
  editingQuestion.value = question
  form.value = {
    type: question.type,
    stem: question.stem,
    explanation: question.explanation || '',
    options: question.options.map(o => ({
      label: o.label,
      content: o.content,
      is_correct: o.is_correct || false,
    })),
  }
  drawerOpen.value = true
}

function addOption() {
  const nextLabel = String.fromCharCode(65 + form.value.options.length)
  form.value.options.push({ label: nextLabel, content: '', is_correct: false })
}

function removeOption(index: number) {
  if (form.value.options.length <= 2) return
  form.value.options.splice(index, 1)
  form.value.options.forEach((option, optionIndex) => { option.label = String.fromCharCode(65 + optionIndex) })
}

function setCorrect(index: number, checked = true) {
  if (form.value.type === 'single') {
    form.value.options.forEach((o, i) => { o.is_correct = i === index })
  } else {
    form.value.options[index].is_correct = checked
  }
}

function resetCorrectForType() {
  form.value.options.forEach((option, index) => { option.is_correct = index === 0 })
}

function optionCount(row: Question) {
  return `${row.options.length} 个选项`
}

function sourceLabel(source: string) {
  const map: Record<string, string> = { manual: '手动', json_import: 'JSON', ai_generated: 'AI' }
  return map[source] || source
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
  if (!form.value.stem.trim()) {
    toast.show('请输入题干', 'error')
    return
  }
  try {
    const payload = { ...form.value, options: form.value.options.map(option => ({ ...option })) }
    if (editingQuestion.value) {
      await updateQuestion(editingQuestion.value.id, payload)
      toast.show('题目已更新', 'success')
    } else {
      await createQuestion(bankId, payload)
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

    <div class="qp-section">
      <div class="qp-toolbar">
        <el-input v-model="keyword" size="small" placeholder="搜索题干" clearable class="!w-[220px]" @input="onKeywordInput" @keyup.enter="load" />
        <el-button size="small" type="primary" @click="openCreate">添加题目</el-button>
      </div>

      <el-table v-loading="loading" :data="questions" size="small" border empty-text="暂无题目">
        <el-table-column type="index" label="#" width="54" />
        <el-table-column label="题型" width="82">
          <template #default="{ row }: { row: Question }">
            <el-tag :type="row.type === 'single' ? 'primary' : 'warning'" size="small">{{ row.type === 'single' ? '单选' : '多选' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="题干" min-width="340">
          <template #default="{ row }: { row: Question }">
            <div class="min-w-0">
              <MathText :key="`question-stem-${row.id}`" as="span" class="line-clamp-2 text-slate-900" :text="row.stem" />
              <MathText v-if="row.explanation" :key="`question-explanation-${row.id}`" as="p" class="mt-1 line-clamp-1 text-sm text-slate-500" :text="row.explanation" />
            </div>
          </template>
        </el-table-column>
        <el-table-column label="选项" width="90">
          <template #default="{ row }: { row: Question }">{{ optionCount(row) }}</template>
        </el-table-column>
        <el-table-column label="来源" width="90">
          <template #default="{ row }: { row: Question }">{{ sourceLabel(row.source) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" align="right" fixed="right">
          <template #default="{ row }: { row: Question }">
            <div class="flex items-center justify-end gap-1">
              <el-button text size="small" @click="editQuestion(row)">编辑</el-button>
              <el-button text type="danger" size="small" @click="removeQuestion(row.id)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-drawer v-model="drawerOpen" :title="drawerTitle" size="680px" @closed="resetForm">
      <el-form class="grid gap-3" label-position="top">
        <div class="flex items-center gap-2">
          <el-select v-model="form.type" size="small" style="width: 100px" @change="resetCorrectForType">
            <el-option value="single" label="单选" />
            <el-option value="multiple" label="多选" />
          </el-select>
        </div>
        <el-form-item label="题干">
          <el-input v-model="form.stem" type="textarea" :rows="5" placeholder="题目内容" />
        </el-form-item>
        <div class="grid gap-2">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-slate-700">选项</span>
            <el-button size="small" @click="addOption">添加选项</el-button>
          </div>
          <div v-for="(option, index) in form.options" :key="index" class="grid grid-cols-[44px_64px_minmax(0,1fr)_56px] items-center gap-2">
            <el-radio
              v-if="form.type === 'single'"
              :model-value="form.options.findIndex(item => item.is_correct)"
              :value="index"
              @change="() => setCorrect(index)"
            />
            <el-checkbox v-else :model-value="option.is_correct" @change="(checked: string | number | boolean) => setCorrect(index, Boolean(checked))" />
            <el-input v-model="option.label" size="small" />
            <el-input v-model="option.content" :placeholder="`选项 ${option.label}`" size="small" />
            <el-button v-if="form.options.length > 2" text size="small" @click="removeOption(index)">移除</el-button>
          </div>
        </div>
        <el-form-item label="解析（可选）">
          <el-input v-model="form.explanation" type="textarea" :rows="4" placeholder="答案解析" />
        </el-form-item>
        <div class="flex justify-end gap-2">
          <el-button @click="resetForm">取消</el-button>
          <el-button type="primary" @click="saveQuestion">{{ editingQuestion ? '更新题目' : '添加题目' }}</el-button>
        </div>
      </el-form>
    </el-drawer>
  </section>
</template>
