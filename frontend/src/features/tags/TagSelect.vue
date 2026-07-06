<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listTags } from '../../api/v2/banks'
import type { QuestionBankTag } from '../../api/types'
import type { TagInputValue } from './tagUtils'

const props = withDefaults(defineProps<{
  modelValue: TagInputValue[]
  placeholder?: string
}>(), {
  placeholder: '搜索或创建标签',
})

const emit = defineEmits<{ 'update:modelValue': [value: TagInputValue[]] }>()

const loading = ref(false)
const remoteTags = ref<QuestionBankTag[]>([])

const mergedOptions = computed(() => {
  const map = new Map<number, QuestionBankTag>()
  for (const tag of remoteTags.value) map.set(tag.id, tag)
  for (const value of props.modelValue) {
    if (value && typeof value !== 'string' && value.id) map.set(value.id, value)
  }
  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name, 'zh-Hans-CN'))
})

async function searchTags(keyword = '') {
  loading.value = true
  try {
    remoteTags.value = (await listTags({ keyword: keyword.trim() || undefined, page_size: 50 })).items
  } catch {
    remoteTags.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => { void searchTags() })
</script>

<template>
  <el-select
    :model-value="modelValue"
    multiple
    filterable
    remote
    allow-create
    default-first-option
    clearable
    value-key="id"
    :loading="loading"
    :placeholder="placeholder"
    :remote-method="searchTags"
    style="width: 100%"
    @update:model-value="emit('update:modelValue', $event as TagInputValue[])"
  >
    <el-option
      v-for="tag in mergedOptions"
      :key="tag.id"
      :label="tag.name"
      :value="tag"
    />
  </el-select>
</template>
