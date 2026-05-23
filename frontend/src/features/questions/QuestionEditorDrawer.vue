<script setup lang="ts">
import { ref, watch } from 'vue'
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
  form.value.options.forEach((option, index) => { option.is_correct = index === 0 })
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
        </el-select>
      </el-form-item>
      <el-form-item label="题干">
        <el-input v-model="form.stem" type="textarea" :rows="5" placeholder="题目内容" />
      </el-form-item>
      <OptionEditor :form="form" />
      <el-form-item label="解析（可选）">
        <el-input v-model="form.explanation" type="textarea" :rows="4" placeholder="答案解析" />
      </el-form-item>
      <el-alert v-if="form.validation_message" :title="form.validation_message" type="warning" show-icon :closable="false" />
      <div class="flex justify-end gap-2">
        <el-button @click="close">取消</el-button>
        <el-button type="primary" @click="submit">{{ confirmText }}</el-button>
      </div>
    </el-form>
  </el-drawer>
</template>
