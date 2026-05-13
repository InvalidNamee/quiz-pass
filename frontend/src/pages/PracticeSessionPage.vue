<script setup lang="ts">
import { onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePracticeSession } from '../composables/usePracticeSession'
import AppLoading from '../components/AppLoading.vue'
import SessionHeader from '../components/practice/SessionHeader.vue'
import QuestionCard from '../components/practice/QuestionCard.vue'
import QuestionNavigator from '../components/practice/QuestionNavigator.vue'

const route = useRoute()
const router = useRouter()
const sessionId = Number(route.params.sessionId)
const {
  session, questions, currentIndex, selected, answerStatus, answerResults,
  loading, currentQuestion, totalQuestions,
  load, toggle, submitAnswer, submitAll, previousQuestion, nextQuestion, goToQuestion,
  isLocked, shouldReveal, questionStatus,
} = usePracticeSession(sessionId)

const navigatorStatuses = computed(() => questions.value.map(q => questionStatus(q.id)))

const showSubmitButton = computed(() => {
  if (!currentQuestion.value) return false
  return currentQuestion.value.type === 'multiple' || session.value?.mode === 'exam'
})

async function handleSubmit() {
  await submitAll()
  router.push(`/practice/result/${sessionId}`)
}

function onKeydown(e: KeyboardEvent) {
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
  if (e.key === 'ArrowLeft' || e.key === 'a') previousQuestion()
  else if (e.key === 'ArrowRight' || e.key === 'd') nextQuestion()
  else if (e.key === 'Enter' && showSubmitButton.value) submitAnswer()
  else {
    const num = parseInt(e.key)
    if (num >= 1 && num <= 9 && currentQuestion.value) {
      const option = currentQuestion.value.options[num - 1]
      if (option) toggle(currentQuestion.value, option.id)
    }
  }
}

onMounted(() => { load(); document.addEventListener('keydown', onKeydown) })
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <AppLoading v-if="loading" />

  <section v-else-if="questions.length" class="grid gap-5">
    <SessionHeader
      :current-index="currentIndex"
      :total-questions="totalQuestions"
      @submit="handleSubmit"
    />

    <div class="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_240px]">
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
  </section>
</template>
