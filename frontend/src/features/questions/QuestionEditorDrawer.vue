<script setup lang="ts">
import { ref, watch } from 'vue'
import BlankAnswerEditor from './BlankAnswerEditor.vue'
import OptionEditor from './OptionEditor.vue'
import { cloneQuestionForm, emptyQuestionForm, validateQuestionForm, type QuestionForm } from './questionForm'
import { useToast } from '../../composables/useToast'

const props = withDefaults(defineProps<{
  modelValue: boolean
  title: string
  initialQuestion?: QuestionForm | null
  confirmText?: string
}>(), {
  confirmText: '确定',
  initialQuestion: null,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [form: QuestionForm]
}>()

const toast = useToast()
const form = ref<QuestionForm>(emptyQuestionForm())

function close() {
  emit('update:modelValue', false)
}

function resetCorrectForType() {
  if (form.value.type === 'single' || form.value.type === 'multiple') {
    if (!form.value.options.length) {
      form.value.options = [
        { label: 'A', content: '', is_correct: true },
        { label: 'B', content: '', is_correct: false },
      ]
    }
    form.value.options.forEach((option, index) => { option.is_correct = index === 0 })
    form.value.blanks = []
  } else if (form.value.type === 'blank') {
    form.value.options = []
    if (!form.value.blanks.length) form.value.blanks = [{ label: '1', answers: [''] }]
  } else {
    form.value.options = []
    form.value.blanks = []
  }
}

function submit() {
  const message = validateQuestionForm(form.value)
  if (message) {
    toast.show(message, 'error')
    return
  }
  emit('confirm', cloneQuestionForm(form.value))
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) return
    form.value = props.initialQuestion ? cloneQuestionForm(props.initialQuestion) : emptyQuestionForm()
  },
  { immediate: true },
)
</script>

<template>
  <el-drawer :model-value="modelValue" :title="title" size="680px" @update:model-value="emit('update:modelValue', $event)">
    <el-form class="grid gap-3" label-position="top">
      <el-form-item label="题型">
        <el-select v-model="form.type" size="small" style="width: 120px" @change="resetCorrectForType">
          <el-option value="single" label="单选" />
          <el-option value="multiple" label="多选" />
          <el-option value="blank" label="填空" />
          <el-option value="short_answer" label="简答" />
        </el-select>
      </el-form-item>
      <el-form-item label="题干">
        <el-input v-model="form.stem" type="textarea" :rows="5" placeholder="题目内容" />
      </el-form-item>
      <OptionEditor v-if="form.type === 'single' || form.type === 'multiple'" :form="form" />
      <BlankAnswerEditor v-if="form.type === 'blank'" :form="form" />
      <el-form-item :label="form.type === 'short_answer' ? '给分点' : '解析（可选）'">
        <el-input v-model="form.explanation" type="textarea" :rows="4" :placeholder="form.type === 'short_answer' ? '填写参考给分点' : '答案解析'" />
      </el-form-item>
      <el-alert v-if="form.validation_message" :title="form.validation_message" type="warning" show-icon :closable="false" />
      <div class="flex justify-end gap-2">
        <el-button @click="close">取消</el-button>
        <el-button type="primary" @click="submit">{{ confirmText }}</el-button>
      </div>
    </el-form>
  </el-drawer>
</template>
