<script setup lang="ts">
import AppButton from '../AppButton.vue'
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
  answer: []
  prev: []
  next: []
}>()

function optionClass(optionId: number) {
  const selected = props.selectedOptionIds.includes(optionId)
  if (props.shouldReveal) {
    if (selected && props.answerStatus === 'wrong') return 'border-red-300 bg-red-50 text-red-700'
    if (selected && props.answerStatus === 'correct') return 'border-emerald-300 bg-emerald-50 text-emerald-700'
    return 'border-slate-100 text-slate-400'
  }
  if (selected) return 'border-brand-500 bg-brand-50 text-brand-800'
  return 'border-slate-200 hover:border-slate-300 text-slate-700'
}
</script>

<template>
  <article :class="['grid self-start gap-4 rounded-xl border p-6', answerStatus === 'correct' ? 'border-emerald-400 bg-emerald-50/20' : answerStatus === 'wrong' ? 'border-red-400 bg-red-50/20' : 'border-slate-200 bg-white']">
    <span class="w-fit rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
      {{ question.type === 'single' ? '单选题' : '多选题' }}
    </span>

    <MathText as="h2" class="text-lg font-semibold leading-relaxed text-slate-900" :text="question.stem" />

    <div class="grid gap-2">
      <label
        v-for="option in question.options"
        :key="option.id"
        class="flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors"
        :class="[optionClass(option.id), isLocked ? 'cursor-default' : 'cursor-pointer']"
      >
        <input
          :type="question.type === 'single' ? 'radio' : 'checkbox'"
          :checked="selectedOptionIds.includes(option.id)"
          :disabled="isLocked"
          class="h-4 w-4 accent-brand-600"
          @change="emit('toggle', option.id)"
        />
        <span class="text-sm">
          <span class="font-medium">{{ option.label }}.</span>
          <MathText class="inline" :text="option.content" />
        </span>
      </label>
    </div>

    <div v-if="showSubmitButton" class="flex gap-2">
      <AppButton :disabled="isLocked || !selectedOptionIds.length" @click="emit('answer')">提交本题</AppButton>
    </div>

    <!-- Answer feedback -->
    <div v-if="answerStatus" class="flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium" :class="answerStatus === 'correct' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'">
      <svg v-if="answerStatus === 'correct'" class="h-5 w-5 shrink-0 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <svg v-else class="h-5 w-5 shrink-0 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {{ answerStatus === 'correct' ? '回答正确' : '回答错误' }}
    </div>

    <!-- Exam mode: submitted but not yet revealed -->
    <div v-else-if="isLocked" class="flex items-center gap-2 rounded-lg bg-slate-100 px-4 py-3 text-sm font-medium text-slate-600">
      <svg class="h-5 w-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
      已提交答案，交卷后公布结果
    </div>

    <!-- Reveal panel -->
    <div v-if="shouldReveal" class="grid gap-2 rounded-lg p-4 text-sm" :class="answerStatus === 'correct' ? 'border border-emerald-200 bg-emerald-50' : 'border border-red-200 bg-red-50'">
      <p class="font-bold" :class="answerStatus === 'correct' ? 'text-emerald-800' : 'text-red-800'">
        正确答案：{{ correctLabels.join('、') }}
      </p>
      <p v-if="explanation" class="text-slate-600">
        <span class="font-medium">解析：</span>
        <MathText class="inline" :text="explanation" />
      </p>
    </div>

    <div class="flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
      <AppButton variant="ghost" :disabled="!canGoPrev" @click="emit('prev')">上一题</AppButton>
      <span class="hidden text-xs text-slate-400 sm:inline">A/D 或 ←/→ 切换 · W/S 跳行</span>
      <AppButton :disabled="!canGoNext" @click="emit('next')">下一题</AppButton>
    </div>
  </article>
</template>
