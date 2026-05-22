<script setup lang="ts">
import MathText from '../MathText.vue'

type Question = {
  id: number
  type: 'single' | 'multiple'
  stem: string
  options: { id: number; label: string; content: string }[]
}

const props = defineProps<{
  question: Question
  selectedOptionIds: number[]
  isLocked: boolean
  shouldReveal: boolean
  answerStatus: 'correct' | 'wrong' | null
  correctLabels: string[]
  explanation: string | null
  showSubmitButton: boolean
  canGoPrev: boolean
  canGoNext: boolean
}>()

const emit = defineEmits<{
  toggle: [optionId: number]
  setSelection: [optionIds: number[]]
  answer: []
  prev: []
  next: []
}>()

function optionClass(optionId: number) {
  const selected = props.selectedOptionIds.includes(optionId)
  if (props.shouldReveal) {
    if (selected && props.answerStatus === 'wrong') return 'is-wrong-choice'
    if (selected && props.answerStatus === 'correct') return 'is-correct-choice'
    return 'is-muted-choice'
  }
  if (selected) return 'is-selected-choice'
  return ''
}

function chooseOption(optionId: number) {
  if (props.isLocked) return
  if (props.question.type === 'single') {
    emit('setSelection', [optionId])
  } else {
    emit('toggle', optionId)
  }
}
</script>

<template>
  <el-card shadow="never" :class="['question-panel', answerStatus === 'correct' ? 'is-correct' : answerStatus === 'wrong' ? 'is-wrong' : '']">
    <div class="mb-3 flex items-center gap-2">
      <el-tag size="small" type="info">{{ question.type === 'single' ? '单选题' : '多选题' }}</el-tag>
      <el-tag v-if="isLocked" size="small" type="info">已锁定</el-tag>
    </div>

    <MathText :key="`stem-${question.id}`" as="h2" class="mb-4 text-lg font-semibold leading-relaxed text-slate-900" :text="question.stem" />

    <div class="grid w-full gap-2">
      <button
        v-for="option in question.options"
        :key="option.id"
        type="button"
        :disabled="isLocked"
        :class="['question-choice', optionClass(option.id)]"
        @click="chooseOption(option.id)"
      >
        <span class="choice-label">{{ option.label }}.</span>
        <MathText :key="`option-${question.id}-${option.id}`" class="min-w-0 flex-1 text-left" :text="option.content" />
      </button>
    </div>

    <div v-if="showSubmitButton" class="mt-5 flex gap-2 pt-1">
      <el-button type="primary" :disabled="isLocked || !selectedOptionIds.length" @click="emit('answer')">提交本题</el-button>
    </div>

    <!-- Answer feedback -->
    <div v-if="answerStatus" class="mt-3 flex items-center gap-2 border px-3 py-2 text-sm" :class="answerStatus === 'correct' ? 'answer-feedback is-correct-feedback' : 'answer-feedback is-wrong-feedback'">
      <span class="answer-feedback-label">{{ answerStatus === 'correct' ? '正确' : '错误' }}</span>
      <span>{{ answerStatus === 'correct' ? '回答正确' : '回答错误' }}</span>
    </div>

    <!-- Exam mode: submitted but not yet revealed -->
    <el-alert v-else-if="isLocked" class="mt-3" type="info" title="已提交答案，交卷后公布结果" show-icon :closable="false" />

    <!-- Reveal panel -->
    <div v-if="shouldReveal" class="mt-3 grid gap-2 border p-3 text-sm" :class="answerStatus === 'correct' ? 'reveal-panel is-correct-reveal' : 'reveal-panel is-wrong-reveal'">
      <p class="font-bold">
        正确答案：{{ correctLabels.join('、') }}
      </p>
      <p v-if="explanation" class="text-slate-600">
        <span class="font-medium">解析：</span>
        <MathText :key="`explanation-${question.id}`" class="inline" :text="explanation" />
      </p>
    </div>

    <div class="mt-4 flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
      <el-button text :disabled="!canGoPrev" @click="emit('prev')">上一题</el-button>
      <span class="hidden text-xs text-slate-400 sm:inline">A/D 或 ←/→ 切换 · W/S 或 ↑/↓ 跳行</span>
      <el-button text :disabled="!canGoNext" @click="emit('next')">下一题</el-button>
    </div>
  </el-card>
</template>

<style scoped>
.question-panel {
  --practice-ok-border: #86efac;
  --practice-ok-bg: #f0fdf4;
  --practice-ok-text: #166534;
  --practice-bad-border: #fda4af;
  --practice-bad-bg: #fff1f2;
  --practice-bad-text: #be123c;
  border-color: var(--qp-border);
}
.question-panel.is-correct {
  border-color: var(--practice-ok-border);
}
.question-panel.is-wrong {
  border-color: var(--practice-bad-border);
}

.question-choice {
  display: flex;
  min-height: 44px;
  width: 100%;
  align-items: flex-start;
  gap: 10px;
  border: 1px solid #d8dee8;
  padding: 10px 12px;
  text-align: left;
  border-color: #d8dee8;
  background: #fff;
  color: #334155;
  transition: border-color .15s ease, background-color .15s ease, color .15s ease;
}
.question-choice:disabled {
  cursor: default;
}
.question-choice:hover {
  border-color: #93c5fd;
  background: #f8fafc;
}
.question-choice.is-selected-choice {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1e40af;
}
.question-choice.is-correct-choice {
  border-color: var(--practice-ok-border);
  background: var(--practice-ok-bg);
  color: var(--practice-ok-text);
}
.question-choice.is-wrong-choice {
  border-color: var(--practice-bad-border);
  background: var(--practice-bad-bg);
  color: var(--practice-bad-text);
}
.question-choice.is-muted-choice {
  border-color: #e5e7eb;
  background: #fff;
  color: #64748b;
}
.choice-label {
  min-width: 24px;
  color: inherit;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.55;
}
.answer-feedback.is-correct-feedback,
.reveal-panel.is-correct-reveal {
  border-color: var(--practice-ok-border);
  background: var(--practice-ok-bg);
  color: var(--practice-ok-text);
}
.answer-feedback.is-wrong-feedback,
.reveal-panel.is-wrong-reveal {
  border-color: var(--practice-bad-border);
  background: var(--practice-bad-bg);
  color: var(--practice-bad-text);
}
.answer-feedback-label {
  font-weight: 700;
  color: inherit;
}
</style>
