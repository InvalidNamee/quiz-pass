<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listTags } from '../api/v2/banks'
import type { QuestionBankTag } from '../api/types'
import AppModal from './AppModal.vue'
import AppButton from './AppButton.vue'

const props = defineProps<{ modelValue: boolean; selected: QuestionBankTag[] }>()
const emit = defineEmits<{ 'update:modelValue': [v: boolean]; 'update:selected': [tags: QuestionBankTag[]] }>()

const keyword = ref('')
const allTags = ref<QuestionBankTag[]>([])
const localSelected = ref<QuestionBankTag[]>([])

async function load() {
  allTags.value = (await listTags({ page_size: 100, keyword: keyword.value.trim() || undefined })).items
}

function toggle(tag: QuestionBankTag) {
  const found = localSelected.value.find(t => t.id === tag.id)
  localSelected.value = found ? localSelected.value.filter(t => t.id !== tag.id) : [...localSelected.value, tag]
}

function apply() {
  emit('update:selected', localSelected.value)
  emit('update:modelValue', false)
}

onMounted(() => {
  localSelected.value = [...props.selected]
  load()
})
</script>

<template>
  <AppModal :model-value="modelValue" title="选择标签" max-width="max-w-md" @update:model-value="emit('update:modelValue', $event)">
    <div class="grid gap-3">
      <input v-model="keyword" class="rounded-input border border-slate-300 px-3 py-2 text-sm" placeholder="搜索标签" @input="load" />
      <div class="flex flex-wrap gap-1.5 max-h-60 overflow-y-auto">
        <button
          v-for="tag in allTags" :key="tag.id"
          class="rounded-full border px-3 py-1 text-sm transition-colors"
          :class="localSelected.some(t => t.id === tag.id) ? 'border-brand-500 bg-brand-50 text-brand-700' : 'border-slate-200 text-slate-600 hover:border-slate-300'"
          @click="toggle(tag)"
        >{{ tag.name }}</button>
      </div>
      <p v-if="!allTags.length" class="text-sm text-slate-400">暂无标签</p>
    </div>
    <template #footer>
      <AppButton variant="ghost" @click="emit('update:modelValue', false)">取消</AppButton>
      <AppButton @click="apply">确定 ({{ localSelected.length }})</AppButton>
    </template>
  </AppModal>
</template>
