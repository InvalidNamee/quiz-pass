<script setup lang="ts">
import { onMounted, onBeforeUnmount, computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { usePracticeSession } from '../composables/usePracticeSession'
import { useToast } from '../composables/useToast'
import SessionHeader from '../components/practice/SessionHeader.vue'
import QuestionCard from '../components/practice/QuestionCard.vue'
import QuestionNavigator from '../components/practice/QuestionNavigator.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const sessionId = Number(route.params.sessionId)
const redirectingToResult = ref(false)
const submitDialogVisible = ref(false)
const commitCachedAnswers = ref(true)
const submittingSession = ref(false)
const {
  session, questions, currentIndex, selected, textAnswers, answerStatus, answerResults,
  loading, currentQuestion, totalQuestions,
  load, toggle, setSelection, setTextAnswers, submitAnswer, submitAll, saveDraftIfChanged, goToQuestion, setCurrentIndex,
  isLocked, shouldReveal, questionStatus,
} = usePracticeSession(sessionId)

const navigatorStatuses = computed(() => questions.value.map(q => questionStatus(q.id)))
const navigatorTypes = computed(() => questions.value.map(q => q.type))
const navigatorTypeOrder = ['single', 'multiple', 'blank', 'short_answer'] as const
const navigatorSections = computed(() => navigatorTypeOrder
  .map((type) => ({
    type,
    indexes: questions.value
      .map((question, index) => ({ question, index }))
      .filter((item) => item.question.type === type)
      .map((item) => item.index),
  }))
  .filter((section) => section.indexes.length))
const visualOrder = computed(() => navigatorSections.value.flatMap((section) => section.indexes))
const currentVisualIndex = computed(() => {
  const index = visualOrder.value.indexOf(currentIndex.value)
  return index >= 0 ? index : currentIndex.value
})

const showSubmitButton = computed(() => {
  if (!currentQuestion.value) return false
  return currentQuestion.value.type !== 'single' || session.value?.mode === 'exam'
})

async function handleSubmit() {
  commitCachedAnswers.value = true
  submitDialogVisible.value = true
}

async function confirmSubmit() {
  try {
    submittingSession.value = true
    await submitAll({ commit_drafts: commitCachedAnswers.value })
    submitDialogVisible.value = false
    router.push(`/practice/result/${sessionId}`)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '提交失败', 'error')
  } finally {
    submittingSession.value = false
  }
}

async function onKeydown(e: KeyboardEvent) {
  const target = e.target as HTMLElement | null
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target?.isContentEditable || target?.closest('[contenteditable="true"]')) return
  if (!totalQuestions.value) return
  const key = e.key.toLowerCase()
  if (e.key === 'ArrowLeft' || key === 'a') {
    e.preventDefault()
    await moveVisualByOffset(-1)
  }
  else if (e.key === 'ArrowRight' || key === 'd') {
    e.preventDefault()
    await moveVisualByOffset(1)
  }
  else if (e.key === 'ArrowUp' || key === 'w') {
    e.preventDefault()
    await moveVisualByRow(-1)
  }
  else if (e.key === 'ArrowDown' || key === 's') {
    e.preventDefault()
    await moveVisualByRow(1)
  }
  else if (e.key === 'Enter' && showSubmitButton.value) {
    e.preventDefault()
    await submitAnswer()
  }
  else {
    const num = parseInt(e.key)
    if (num >= 1 && num <= 9 && currentQuestion.value) {
      e.preventDefault()
      const option = currentQuestion.value.options[num - 1]
      if (option) toggle(currentQuestion.value, option.id)
    }
  }
}

async function moveVisualByOffset(offset: number) {
  const order = visualOrder.value
  const position = order.indexOf(currentIndex.value)
  if (position < 0) return
  const nextPosition = Math.min(order.length - 1, Math.max(0, position + offset))
  if (nextPosition !== position) await goToQuestion(order[nextPosition])
}

async function moveVisualByRow(direction: -1 | 1) {
  const sections = navigatorSections.value
  const sectionIndex = sections.findIndex((section) => section.indexes.includes(currentIndex.value))
  if (sectionIndex < 0) return
  const section = sections[sectionIndex]
  const localIndex = section.indexes.indexOf(currentIndex.value)
  const column = localIndex % 5
  const sameSectionTarget = localIndex + direction * 5
  if (sameSectionTarget >= 0 && sameSectionTarget < section.indexes.length) {
    await goToQuestion(section.indexes[sameSectionTarget])
    return
  }
  const nextSection = sections[sectionIndex + direction]
  if (!nextSection) return
  if (direction < 0) {
    const lastRowStart = Math.floor((nextSection.indexes.length - 1) / 5) * 5
    const target = Math.min(nextSection.indexes.length - 1, lastRowStart + column)
    await goToQuestion(nextSection.indexes[target])
    return
  }
  const target = Math.min(column, nextSection.indexes.length - 1)
  await goToQuestion(nextSection.indexes[target])
}

async function loadOrRedirectFinishedSession() {
  try {
    await load()
    if (session.value && session.value.status !== 'in_progress') {
      redirectingToResult.value = true
      await ElMessageBox.alert('本次练习已经结束，将为你打开结果页。', '练习已结束', {
        confirmButtonText: '查看结果',
        type: 'info',
      }).catch(() => undefined)
      router.replace(`/practice/result/${sessionId}`)
      return
    }
    if (route.query.resume === '1') {
      const firstUnansweredVisual = visualOrder.value.find((index) => !questions.value[index]?.answer_state?.is_answered)
      setCurrentIndex(firstUnansweredVisual ?? visualOrder.value[0] ?? 0)
    } else {
      setCurrentIndex(visualOrder.value[0] ?? 0)
    }
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '加载练习失败', 'error')
  }
}

onMounted(() => { void loadOrRedirectFinishedSession(); document.addEventListener('keydown', onKeydown) })
watch(() => session.value?.status, async (status) => {
  if (status !== 'submitted' || redirectingToResult.value) return
  redirectingToResult.value = true
  await ElMessageBox.alert('本次练习已经结束，将为你打开结果页。', '练习已结束', {
    confirmButtonText: '查看结果',
    type: 'info',
  }).catch(() => undefined)
  router.replace(`/practice/result/${sessionId}`)
})
onBeforeUnmount(() => {
  void saveDraftIfChanged()
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <section v-loading="loading" class="qp-page" element-loading-text="加载中...">
    <template v-if="questions.length && !redirectingToResult">
      <SessionHeader
        :current-index="currentVisualIndex"
        :total-questions="totalQuestions"
        @submit="handleSubmit"
      />

      <div class="grid items-start gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
        <QuestionCard
          v-if="currentQuestion"
          :question="currentQuestion"
          :selected-option-ids="selected[currentQuestion.id] ?? []"
          :text-answers="textAnswers[currentQuestion.id] ?? []"
          :is-locked="isLocked(currentQuestion.id)"
          :should-reveal="shouldReveal(currentQuestion.id)"
          :answer-status="answerStatus[currentQuestion.id] || null"
          :correct-labels="answerResults[currentQuestion.id]?.correct_labels ?? []"
          :correct-text-answers="answerResults[currentQuestion.id]?.correct_text_answers ?? []"
          :explanation="answerResults[currentQuestion.id]?.explanation ?? null"
          :show-submit-button="showSubmitButton"
          :can-go-prev="currentVisualIndex > 0"
          :can-go-next="currentVisualIndex < totalQuestions - 1"
          @toggle="toggle(currentQuestion!, $event)"
          @set-selection="setSelection(currentQuestion!, $event)"
          @set-text-answers="setTextAnswers(currentQuestion!, $event)"
          @answer="submitAnswer()"
          @prev="moveVisualByOffset(-1)"
          @next="moveVisualByOffset(1)"
        />

        <QuestionNavigator
          :total="totalQuestions"
          :current-index="currentIndex"
          :statuses="navigatorStatuses"
          :types="navigatorTypes"
          @go="goToQuestion"
        />
      </div>

      <el-dialog v-model="submitDialogVisible" title="提交试卷" width="460px" append-to-body>
        <div class="grid gap-3 text-sm leading-relaxed text-slate-600">
          <p class="m-0">提交后将结算本次练习，已锁定或已提交的题目不能再修改。</p>
          <el-radio-group v-model="commitCachedAnswers" class="grid gap-2">
            <el-radio :value="true" border>提交当前已缓存答案并计分</el-radio>
            <el-radio :value="false" border>不提交未锁定缓存，按未作答处理</el-radio>
          </el-radio-group>
        </div>
        <template #footer>
          <el-button @click="submitDialogVisible = false">继续作答</el-button>
          <el-button type="primary" :loading="submittingSession" @click="confirmSubmit">提交试卷</el-button>
        </template>
      </el-dialog>
    </template>
  </section>
</template>
