<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { AIGenerationDraftQuestion, Question, QuestionBankV2 } from '../api/types'
import { createQuestion, deleteQuestion, getBank, listQuestions, updateQuestion } from '../api/v2/banks'
import { useToast } from '../composables/useToast'
import QuestionEditorDrawer from '../features/questions/QuestionEditorDrawer.vue'
import QuestionTable from '../features/questions/QuestionTable.vue'
import { emptyQuestionForm, formToQuestionPayload, questionToForm, type QuestionForm } from '../features/questions/questionForm'

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
const editorInitialQuestion = ref<QuestionForm>(emptyQuestionForm())
const drawerTitle = computed(() => editingQuestion.value ? '编辑题目' : '添加题目')

function openCreate() {
  editingQuestion.value = null
  editorInitialQuestion.value = emptyQuestionForm()
  drawerOpen.value = true
}

function editQuestion(question: Question | AIGenerationDraftQuestion) {
  editingQuestion.value = question as Question
  editorInitialQuestion.value = questionToForm(question)
  drawerOpen.value = true
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
    const data = await listQuestions(bankId, { keyword: keyword.value.trim() || undefined, all: true })
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

async function saveQuestion(form: QuestionForm) {
  try {
    const payload = formToQuestionPayload(form)
    if (editingQuestion.value) {
      await updateQuestion(editingQuestion.value.id, payload)
      toast.show('题目已更新', 'success')
    } else {
      await createQuestion(bankId, payload)
      toast.show('题目已添加', 'success')
    }
    drawerOpen.value = false
    editingQuestion.value = null
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

      <QuestionTable :questions="questions" :loading="loading" show-source empty-text="暂无题目">
        <template #actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <el-button text size="small" @click="editQuestion(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="removeQuestion(row.id)">删除</el-button>
          </div>
        </template>
      </QuestionTable>
    </div>

    <QuestionEditorDrawer
      v-model="drawerOpen"
      :title="drawerTitle"
      :initial-question="editorInitialQuestion"
      :confirm-text="editingQuestion ? '更新题目' : '添加题目'"
      @confirm="saveQuestion"
    />
  </section>
</template>
