<script setup lang="ts">
import type { QuestionForm } from './questionForm'
import { MAX_OPTION_COUNT } from './questionForm'

const props = defineProps<{ form: QuestionForm }>()

function relabelBlanks() {
  props.form.blanks.forEach((blank, index) => { blank.label = String(index + 1) })
}

function addBlank() {
  if (props.form.blanks.length >= MAX_OPTION_COUNT) return
  props.form.blanks.push({ label: String(props.form.blanks.length + 1), answers: [''] })
}

function removeBlank(index: number) {
  if (props.form.blanks.length <= 1) return
  props.form.blanks.splice(index, 1)
  relabelBlanks()
}

function addAnswer(index: number) {
  props.form.blanks[index].answers.push('')
}

function removeAnswer(blankIndex: number, answerIndex: number) {
  if (props.form.blanks[blankIndex].answers.length <= 1) return
  props.form.blanks[blankIndex].answers.splice(answerIndex, 1)
}

function insertPlaceholder(label: string) {
  const placeholder = `{{${label}}}`
  if (!props.form.stem.includes(placeholder)) {
    props.form.stem = `${props.form.stem}${props.form.stem ? ' ' : ''}${placeholder}`
  }
}

function placeholderLabel(label: string) {
  return `{{${label}}}`
}
</script>

<template>
  <div class="grid gap-3">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-slate-700">填空答案</span>
      <div class="flex items-center gap-2">
        <span v-if="form.blanks.length >= MAX_OPTION_COUNT" class="text-xs text-slate-500">最多 26 个空</span>
        <el-button size="small" :disabled="form.blanks.length >= MAX_OPTION_COUNT" @click="addBlank">添加空</el-button>
      </div>
    </div>
    <div v-for="(blank, blankIndex) in form.blanks" :key="blank.label" class="rounded-lg border border-slate-200 p-3">
      <div class="mb-2 flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 text-sm font-semibold text-slate-700">
          <span>空 {{ blank.label }}</span>
          <el-button size="small" text @click="insertPlaceholder(blank.label)">插入 {{ placeholderLabel(blank.label) }}</el-button>
        </div>
        <el-button v-if="form.blanks.length > 1" size="small" text type="danger" @click="removeBlank(blankIndex)">移除空</el-button>
      </div>
      <div class="grid gap-2">
        <div v-for="(_, answerIndex) in blank.answers" :key="answerIndex" class="flex items-center gap-2">
          <el-input v-model="blank.answers[answerIndex]" size="small" :placeholder="`空 ${blank.label} 的可接受答案 ${answerIndex + 1}`" />
          <el-button v-if="blank.answers.length > 1" size="small" text @click="removeAnswer(blankIndex, answerIndex)">移除</el-button>
        </div>
      </div>
      <el-button class="mt-2" size="small" @click="addAnswer(blankIndex)">添加同义答案</el-button>
    </div>
  </div>
</template>
