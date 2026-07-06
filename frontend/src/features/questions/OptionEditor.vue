<script setup lang="ts">
import type { CheckboxValueType } from 'element-plus'
import type { QuestionForm } from './questionForm'
import { MAX_OPTION_COUNT, relabelOptions } from './questionForm'

const props = defineProps<{ form: QuestionForm }>()

function addOption() {
  if (props.form.options.length >= MAX_OPTION_COUNT) return
  props.form.options.push({ label: String.fromCharCode(65 + props.form.options.length), content: '', is_correct: false })
}

function removeOption(index: number) {
  if (props.form.options.length <= 2) return
  props.form.options.splice(index, 1)
  relabelOptions(props.form.options)
  if (!props.form.options.some((option) => option.is_correct)) props.form.options[0].is_correct = true
}

function setCorrect(index: number, checked: CheckboxValueType = true) {
  if (props.form.type === 'single') {
    props.form.options.forEach((option, optionIndex) => { option.is_correct = optionIndex === index })
  } else {
    props.form.options[index].is_correct = Boolean(checked)
  }
}
</script>

<template>
  <div class="grid gap-2">
    <div class="flex items-center justify-between">
      <span class="text-sm font-medium text-slate-700">选项</span>
      <div class="flex items-center gap-2">
        <span v-if="form.options.length >= MAX_OPTION_COUNT" class="text-xs text-slate-500">最多 26 个选项</span>
        <el-button size="small" :disabled="form.options.length >= MAX_OPTION_COUNT" @click="addOption">添加选项</el-button>
      </div>
    </div>
    <div v-for="(option, index) in form.options" :key="index" class="grid grid-cols-[32px_48px_minmax(0,1fr)_48px] items-start gap-2">
      <el-radio
        v-if="form.type === 'single'"
        :model-value="form.options.findIndex(item => item.is_correct)"
        :value="index"
        @change="() => setCorrect(index)"
      />
      <el-checkbox v-else :model-value="option.is_correct" @change="(checked: CheckboxValueType) => setCorrect(index, checked)" />
      <span class="pt-1.5 text-center text-sm font-medium text-slate-600">{{ option.label }}</span>
      <el-input v-model="option.content" type="textarea" :autosize="{ minRows: 1, maxRows: 5 }" :placeholder="`选项 ${option.label}`" />
      <el-button v-if="form.options.length > 2" text size="small" @click="removeOption(index)">移除</el-button>
    </div>
  </div>
</template>
