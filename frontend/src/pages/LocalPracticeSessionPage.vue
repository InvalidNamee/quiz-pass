<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useLocalPracticeSession } from '../composables/useLocalPracticeSession'
import { useToast } from '../composables/useToast'
import SessionHeader from '../components/practice/SessionHeader.vue'
import QuestionCard from '../components/practice/QuestionCard.vue'
import QuestionNavigator from '../components/practice/QuestionNavigator.vue'
import { isUtilityWindowSupported } from '../features/utility-windows/utilityWindow'
import { openSubmitPracticeWindow } from '../features/utility-windows/openUtilityFlows'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const sessionId = Number(route.params.localSessionId)
const submitDialogVisible = ref(false)
const commitCachedAnswers = ref(true)
const submittingSession = ref(false)

const {
  session, questions, currentIndex, selected, textAnswers, answerStatus, answerResults,
  loading, currentQuestion, totalQuestions,
  load, toggle, setSelection, setTextAnswers, submitAnswer, submitAll, saveDraftIfChanged, goToQuestion, setCurrentIndex,
  isLocked, shouldReveal, questionStatus,
} = useLocalPracticeSession(sessionId)

const navigatorStatuses = computed(() => questions.value.map((q) => questionStatus(q.id)))
const navigatorTypes = computed(() => questions.value.map((q) => q.type))
const typeOrder = ['single', 'multiple', 'blank', 'short_answer'] as const
const visualOrder = computed(() => typeOrder.flatMap((type) => questions.value.map((question, index) => ({ question, index })).filter((item) => item.question.type === type).map((item) => item.index)))
const currentVisualIndex = computed(() => Math.max(0, visualOrder.value.indexOf(currentIndex.value)))
const showSubmitButton = computed(() => currentQuestion.value ? currentQuestion.value.type !== 'single' || session.value?.mode === 'exam' : false)

async function moveVisualByOffset(offset: number) {
  const position = visualOrder.value.indexOf(currentIndex.value)
  const next = Math.min(visualOrder.value.length - 1, Math.max(0, position + offset))
  if (next !== position) await goToQuestion(visualOrder.value[next])
}

async function moveVisualByRow(direction: -1 | 1) {
  const position = visualOrder.value.indexOf(currentIndex.value)
  const next = Math.min(visualOrder.value.length - 1, Math.max(0, position + direction * 5))
  if (next !== position) await goToQuestion(visualOrder.value[next])
}

async function onKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target?.isContentEditable) return
  const key = event.key.toLowerCase()
  if (event.key === 'ArrowLeft' || key === 'a') { event.preventDefault(); await moveVisualByOffset(-1) }
  else if (event.key === 'ArrowRight' || key === 'd') { event.preventDefault(); await moveVisualByOffset(1) }
  else if (event.key === 'ArrowUp' || key === 'w') { event.preventDefault(); await moveVisualByRow(-1) }
  else if (event.key === 'ArrowDown' || key === 's') { event.preventDefault(); await moveVisualByRow(1) }
  else if (event.key === 'Enter' && showSubmitButton.value) { event.preventDefault(); await submitAnswer() }
  else {
    const num = Number.parseInt(event.key)
    const option = currentQuestion.value?.options[num - 1]
    if (num >= 1 && num <= 9 && option && currentQuestion.value) {
      event.preventDefault()
      await toggle(currentQuestion.value, option.id)
    }
  }
}

async function openSubmitWindow() {
  commitCachedAnswers.value = true
  if (isUtilityWindowSupported()) {
    await openSubmitPracticeWindow({ sessionId, local: true }).catch((err) => toast.show(err instanceof Error ? err.message : '打开提交窗口失败', 'error'))
    return
  }
  submitDialogVisible.value = true
}

async function confirmSubmit(commitDrafts = commitCachedAnswers.value) {
  submittingSession.value = true
  try {
    await submitAll({ commit_drafts: commitDrafts })
    submitDialogVisible.value = false
    router.push(`/local/practice/result/${sessionId}`)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '提交失败', 'error')
  } finally {
    submittingSession.value = false
  }
}

function handleUtilityCompleted(event: Event) {
  const detail = (event as CustomEvent<{ kind?: string; action?: string; result?: { sessionId?: number; local?: boolean; commitDrafts?: boolean } }>).detail
  if (detail?.kind !== 'submit-practice' || detail.action !== 'submit-choice') return
  if (!detail.result?.local || detail.result.sessionId !== sessionId) return
  void confirmSubmit(Boolean(detail.result.commitDrafts))
}

onMounted(async () => {
  await load()
  setCurrentIndex(visualOrder.value[0] ?? 0)
  document.addEventListener('keydown', onKeydown)
  window.addEventListener('quiz-pass:utility-window-completed', handleUtilityCompleted)
})

onBeforeUnmount(() => {
  void saveDraftIfChanged()
  document.removeEventListener('keydown', onKeydown)
  window.removeEventListener('quiz-pass:utility-window-completed', handleUtilityCompleted)
})
</script>

<template>
  <section v-loading="loading" class="qp-page" element-loading-text="加载本地练习...">
    <template v-if="questions.length">
      <SessionHeader :current-index="currentVisualIndex" :total-questions="totalQuestions" @submit="openSubmitWindow" />

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
        <QuestionNavigator :total="totalQuestions" :current-index="currentIndex" :statuses="navigatorStatuses" :types="navigatorTypes" @go="goToQuestion" />
      </div>

      <el-dialog v-model="submitDialogVisible" title="提交本地练习" width="460px" append-to-body>
        <div class="grid gap-3 text-sm text-slate-600">
          <p class="m-0">提交后会在本机结算。联网后可从本地题库页同步到服务器。</p>
          <el-radio-group v-model="commitCachedAnswers" class="grid gap-2">
            <el-radio :value="true" border>提交当前已缓存答案并计分</el-radio>
            <el-radio :value="false" border>不提交未锁定缓存，按未作答处理</el-radio>
          </el-radio-group>
        </div>
        <template #footer>
          <el-button @click="submitDialogVisible = false">继续作答</el-button>
          <el-button type="primary" :loading="submittingSession" @click="confirmSubmit">提交</el-button>
        </template>
      </el-dialog>
    </template>
  </section>
</template>
