<script setup lang="ts">
import { ref } from 'vue'
import type { QuestionBankTag } from '../../api/types'
import { createBank } from '../../api/v2/banks'
import AppModal from '../AppModal.vue'
import AppButton from '../AppButton.vue'
import BankTagInput from '../BankTagInput.vue'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean]; created: [] }>()

const title = ref('')
const tags = ref<QuestionBankTag[]>([])
const creating = ref(false)

function reset() { title.value = ''; tags.value = [] }

async function submit() {
  if (!title.value.trim()) return
  creating.value = true
  try {
    await createBank({ title: title.value.trim(), visibility: 'private', tag_names: tags.value.map(t => t.name) })
    emit('update:modelValue', false)
    reset()
    emit('created')
  } finally { creating.value = false }
}
</script>

<template>
  <AppModal :model-value="modelValue" title="新建题库" @update:model-value="v => { if (!v) reset(); emit('update:modelValue', v) }">
    <label class="block">
      <span class="mb-1 block text-sm font-medium text-slate-700">题库名称</span>
      <input v-model="title" class="w-full rounded-input border border-slate-300 px-3 py-2 text-sm" placeholder="输入名称" @keyup.enter="submit" />
    </label>
    <div class="mt-4"><BankTagInput v-model="tags" allow-create /></div>
    <template #footer>
      <AppButton variant="ghost" @click="emit('update:modelValue', false); reset()">取消</AppButton>
      <AppButton :loading="creating" :disabled="!title.trim()" @click="submit">创建</AppButton>
    </template>
  </AppModal>
</template>
