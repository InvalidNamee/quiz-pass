<script setup lang="ts">
import { onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { usePracticeSession } from '../composables/usePracticeSession'
import SessionHeader from '../components/practice/SessionHeader.vue'
import QuestionCard from '../components/practice/QuestionCard.vue'
import QuestionNavigator from '../components/practice/QuestionNavigator.vue'

const route = useRoute()
const router = useRouter()
const sessionId = Number(route.params.sessionId)
const {
  session, questions, currentIndex, selected, answerStatus, answerResults,
  loading, currentQuestion, totalQuestions,
  load, toggle, setSelection, submitAnswer, submitAll, saveDraftIfChanged, previousQuestion, nextQuestion, goToQuestion,
  isLocked, shouldReveal, questionStatus,
} = usePracticeSession(sessionId)

const navigatorStatuses = computed(() => questions.value.map(q => questionStatus(q.id)))

const showSubmitButton = computed(() => {
  if (!currentQuestion.value) return false
  return currentQuestion.value.type === 'multiple' || session.value?.mode === 'exam'
})

async function handleSubmit() {
  try {
    await ElMessageBox.confirm('提交后将结算本次练习，已作答题目不能再修改。确定提交试卷吗？', '提交试卷', {
      confirmButtonText: '提交试卷',
      cancelButtonText: '继续作答',
      type: 'warning',
    })
    await submitAll()
    router.push(`/practice/result/${sessionId}`)
  } catch {
    // 用户取消提交
  }
}

async function onKeydown(e: KeyboardEvent) {
  const target = e.target as HTMLElement | null
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target?.isContentEditable || target?.closest('[contenteditable="true"]')) return
  if (!totalQuestions.value) return
  const key = e.key.toLowerCase()
  if (e.key === 'ArrowLeft' || key === 'a') {
    e.preventDefault()
    await previousQuestion()
  }
  else if (e.key === 'ArrowRight' || key === 'd') {
    e.preventDefault()
    await nextQuestion()
  }
  else if (e.key === 'ArrowUp' || key === 'w') {
    e.preventDefault()
    const target = currentIndex.value - 5
    if (target >= 0) await goToQuestion(target)
  }
  else if (e.key === 'ArrowDown' || key === 's') {
    e.preventDefault()
    const target = currentIndex.value + 5
    if (target < totalQuestions.value) await goToQuestion(target)
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

onMounted(() => { load(); document.addEventListener('keydown', onKeydown) })
onBeforeUnmount(() => {
  void saveDraftIfChanged()
  document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <section v-loading="loading" class="qp-page" element-loading-text="加载中...">
    <template v-if="questions.length">
      <SessionHeader
        :current-index="currentIndex"
        :total-questions="totalQuestions"
        @submit="handleSubmit"
      />

      <div class="grid items-start gap-3 lg:grid-cols-[minmax(0,1fr)_220px]">
        <QuestionCard
          v-if="currentQuestion"
          :question="currentQuestion"
          :selected-option-ids="selected[currentQuestion.id] ?? []"
          :is-locked="isLocked(currentQuestion.id)"
          :should-reveal="shouldReveal(currentQuestion.id)"
          :answer-status="answerStatus[currentQuestion.id] || null"
          :correct-labels="answerResults[currentQuestion.id]?.correct_labels ?? []"
          :explanation="answerResults[currentQuestion.id]?.explanation ?? null"
          :show-submit-button="showSubmitButton"
          :can-go-prev="currentIndex > 0"
          :can-go-next="currentIndex < totalQuestions - 1"
          @toggle="toggle(currentQuestion!, $event)"
          @set-selection="setSelection(currentQuestion!, $event)"
          @answer="submitAnswer()"
          @prev="previousQuestion()"
          @next="nextQuestion()"
        />

        <QuestionNavigator
          :total="totalQuestions"
          :current-index="currentIndex"
          :statuses="navigatorStatuses"
          @go="goToQuestion"
        />
      </div>
    </template>
  </section>
</template>
