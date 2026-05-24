<script setup lang="ts">
import { Lightbulb, Target, Zap, CircleCheck, CircleX } from '@lucide/vue'
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
  <el-card shadow="never" :class="['!rounded-2xl question-panel !border-slate-100 shadow-sm transition-all p-2', answerStatus === 'correct' ? 'is-correct' : answerStatus === 'wrong' ? 'is-wrong' : '']">
    <div class="mb-4 flex items-center gap-2">
      <el-tag size="small" class="!rounded-md" type="info">{{ question.type === 'single' ? '单选题' : '多选题' }}</el-tag>
      <el-tag v-if="isLocked" size="small" class="!rounded-md" type="warning">已提交</el-tag>
    </div>

    <MathText :key="`stem-${question.id}`" as="h2" class="mb-5 text-[16px] font-extrabold leading-relaxed text-slate-800" :text="question.stem" />

    <div class="grid w-full gap-2.5">
      <button
        v-for="option in question.options"
        :key="option.id"
        type="button"
        :disabled="isLocked"
        :class="['group question-choice cursor-pointer', optionClass(option.id)]"
        @click="chooseOption(option.id)"
      >
        <!-- Circle circular index badge -->
        <span class="choice-badge flex h-6.5 w-6.5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-500 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors duration-200">
          {{ option.label }}
        </span>
        <MathText :key="`option-${question.id}-${option.id}`" class="choice-text min-w-0 flex-1 text-left text-sm leading-relaxed" :text="option.content" />
      </button>
    </div>

    <div v-if="showSubmitButton" class="mt-5 flex gap-2 pt-1">
      <el-button type="primary" :disabled="isLocked || !selectedOptionIds.length" class="!rounded-xl shadow-md shadow-indigo-500/10 active:scale-95 transition-all" @click="emit('answer')"><Zap :size="14" class="mr-1" />提交答案</el-button>
    </div>

    <!-- Answer feedback -->
    <div v-if="answerStatus" class="mt-4 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm" :class="answerStatus === 'correct' ? 'answer-feedback is-correct-feedback' : 'answer-feedback is-wrong-feedback'">
      <span class="font-extrabold text-base" :class="answerStatus === 'correct' ? 'text-emerald-600' : 'text-rose-600'"><CircleCheck v-if="answerStatus === 'correct'" :size="16" class="text-emerald-600" /><CircleX v-else :size="16" class="text-rose-600" /></span>
      <span class="font-bold text-slate-700">{{ answerStatus === 'correct' ? '回答正确！太棒了' : '回答错误，再接再厉' }}</span>
    </div>

    <!-- Exam mode: submitted but not yet revealed -->
    <el-alert v-else-if="isLocked" class="mt-4 !rounded-xl" type="info" title="已成功提交作答，交卷后将统一公布解析结果" show-icon :closable="false" />

    <!-- Reveal panel -->
    <div v-if="shouldReveal" class="mt-4 grid gap-2.5 rounded-xl border p-4 text-sm leading-relaxed" :class="answerStatus === 'correct' ? 'reveal-panel is-correct-reveal' : 'reveal-panel is-wrong-reveal'">
      <p class="font-extrabold text-slate-800 text-sm">
        <Target :size="14" class="mr-1" />正确答案：<span class="text-emerald-600 font-mono tracking-wider font-extrabold">{{ correctLabels.join('、') }}</span>
      </p>
      <div v-if="explanation" class="text-slate-500 border-t border-slate-100/50 pt-2 mt-1">
        <span class="font-bold text-slate-800"><Lightbulb :size="14" class="mr-1" />题目解析：</span>
        <MathText :key="`explanation-${question.id}`" class="inline" :text="explanation" />
      </div>
    </div>

    <div class="mt-5 flex items-center justify-between gap-3 border-t border-slate-100/60 pt-4">
      <el-button text :disabled="!canGoPrev" class="!rounded-lg" @click="emit('prev')">上一题</el-button>

      <!-- Keyboards legend cap -->
      <div class="hidden text-[11px] text-slate-400 sm:flex items-center gap-1">
        快捷键：
        <kbd>A</kbd>/<kbd>D</kbd> 或 <kbd>←</kbd>/<kbd>→</kbd> 切换 ·
        <kbd>W</kbd>/<kbd>S</kbd> 或 <kbd>↑</kbd>/<kbd>↓</kbd> 跳行 ·
        <kbd>1</kbd>-<kbd>9</kbd> 选择
      </div>

      <el-button text :disabled="!canGoNext" class="!rounded-lg" @click="emit('next')">下一题</el-button>
    </div>
  </el-card>
</template>

<style scoped>
.question-panel {
  --practice-ok-border: rgba(16, 185, 129, 0.4);
  --practice-ok-bg: #f0fdf4;
  --practice-ok-text: #15803d;
  --practice-bad-border: rgba(239, 68, 68, 0.3);
  --practice-bad-bg: #fef2f2;
  --practice-bad-text: #b91c1c;
}
.question-panel.is-correct {
  border-color: var(--practice-ok-border) !important;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.05) !important;
}
.question-panel.is-wrong {
  border-color: var(--practice-bad-border) !important;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.05) !important;
}

.question-choice {
  display: flex;
  min-height: 48px;
  width: 100%;
  align-items: flex-start;
  gap: 12px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-radius: 12px;
  padding: 12px 14px;
  text-align: left;
  background: #fff;
  color: #334155;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.01);
}
.question-choice:disabled {
  cursor: default;
}
.question-choice:hover:not(:disabled) {
  border-color: #a5b4fc;
  background: #fdfdfd;
  transform: translateY(-0.5px);
  box-shadow: 0 4px 6px -1px rgba(99, 102, 241, 0.04);
}
.question-choice:active:not(:disabled) {
  transform: scale(0.99);
}
.question-choice:hover:not(:disabled) .choice-badge {
  background: #e0e7ff;
  color: #4f46e5;
}
.question-choice.is-selected-choice {
  border-color: #818cf8;
  background: #f5f3ff;
  box-shadow: 0 4px 8px -2px rgba(99, 102, 241, 0.08);
}
.question-choice.is-selected-choice .choice-badge {
  background: #6366f1;
  color: #fff;
}
.question-choice .choice-text {
  color: #334155;
}
.question-choice.is-correct-choice {
  border-color: #34d399;
  background: var(--practice-ok-bg);
}
.question-choice.is-correct-choice .choice-badge {
  background: #10b981;
  color: #fff;
}
.question-choice.is-wrong-choice {
  border-color: #f87171;
  background: var(--practice-bad-bg);
}
.question-choice.is-wrong-choice .choice-badge {
  background: #ef4444;
  color: #fff;
}
.question-choice.is-muted-choice {
  border-color: #f1f5f9;
  background: #fff;
}
.question-choice.is-muted-choice .choice-badge {
  background: #f8fafc;
  color: #cbd5e1;
}

.answer-feedback.is-correct-feedback,
.reveal-panel.is-correct-reveal {
  border-color: rgba(16, 185, 129, 0.2);
  background: var(--practice-ok-bg);
  color: #334155;
}
.answer-feedback.is-wrong-feedback,
.reveal-panel.is-wrong-reveal {
  border-color: rgba(239, 68, 68, 0.15);
  background: var(--practice-bad-bg);
  color: #334155;
}
</style>
