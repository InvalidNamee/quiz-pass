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
</script>

<template>
  <el-card shadow="never" :class="['question-panel', answerStatus === 'correct' ? 'is-correct' : answerStatus === 'wrong' ? 'is-wrong' : '']">
    <div class="mb-3 flex items-center gap-2">
      <el-tag size="small" type="info">{{ question.type === 'single' ? '单选题' : '多选题' }}</el-tag>
      <el-tag v-if="isLocked" size="small" type="info">已锁定</el-tag>
    </div>

    <MathText as="h2" class="mb-4 text-lg font-semibold leading-relaxed text-slate-900" :text="question.stem" />

    <el-radio-group
      v-if="question.type === 'single'"
      :model-value="selectedOptionIds[0]"
      class="grid w-full gap-2"
      :disabled="isLocked"
      @change="(value: string | number | boolean | undefined) => emit('setSelection', value === undefined ? [] : [Number(value)])"
    >
      <el-radio
        v-for="option in question.options"
        :key="option.id"
        :value="option.id"
        border
        :class="['question-choice !m-0 !h-auto !w-full !items-start !px-3 !py-3', optionClass(option.id)]"
      >
        <span class="choice-label">{{ option.label }}.</span>
        <MathText class="inline" :text="option.content" />
      </el-radio>
    </el-radio-group>

    <el-checkbox-group
      v-else
      :model-value="selectedOptionIds"
      class="grid w-full gap-2"
      :disabled="isLocked"
      @change="(value: unknown[]) => emit('setSelection', value.map(Number))"
    >
      <el-checkbox
        v-for="option in question.options"
        :key="option.id"
        :value="option.id"
        border
        :class="['question-choice !m-0 !h-auto !w-full !items-start !px-3 !py-3', optionClass(option.id)]"
      >
        <span class="choice-label">{{ option.label }}.</span>
        <MathText class="inline" :text="option.content" />
      </el-checkbox>
    </el-checkbox-group>

    <div v-if="showSubmitButton" class="flex gap-2">
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
        <MathText class="inline" :text="explanation" />
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
  border-color: #d8dee8;
  background: #fff;
  color: #334155;
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
.question-choice :deep(.el-radio__input),
.question-choice :deep(.el-checkbox__input) {
  display: none;
}
.question-choice :deep(.el-radio__label),
.question-choice :deep(.el-checkbox__label) {
  display: inline-flex;
  align-items: flex-start;
  gap: 10px;
  padding-left: 0;
  color: inherit;
  line-height: 1.55;
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
