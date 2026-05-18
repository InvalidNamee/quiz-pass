<script setup lang="ts">
import { ref } from 'vue'
import { listTags } from '../api/v2/banks'
import type { Page, QuestionBankTag } from '../api/types'

const props = withDefaults(defineProps<{
  modelValue: QuestionBankTag[]
  label?: string
  allowCreate?: boolean
  placeholder?: string
}>(), {
  label: '标签',
  placeholder: '搜索或输入标签',
})

const emit = defineEmits<{
  'update:modelValue': [value: QuestionBankTag[]]
}>()

const keyword = ref('')
const tags = ref<QuestionBankTag[]>([])
const loading = ref(false)
const focused = ref(false)
let debounceTimer: ReturnType<typeof setTimeout>

async function search() {
  loading.value = true
  try {
    const result = await listTags({ page_size: 8, keyword: keyword.value.trim() || undefined })
    tags.value = result.items.filter(t => !props.modelValue.some(v => v.id === t.id))
  } finally {
    loading.value = false
  }
}

function onInput() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(search, 200)
}

function choose(tag: QuestionBankTag) {
  if (!props.modelValue.some(item => item.id === tag.id)) {
    emit('update:modelValue', [...props.modelValue, tag])
  }
  keyword.value = ''
  tags.value = []
}

function addNew() {
  const name = keyword.value.trim()
  if (!props.allowCreate || !name || name.length > 32) return
  if (!props.modelValue.some(item => item.name === name)) {
    emit('update:modelValue', [...props.modelValue, { id: 0, name }])
  }
  keyword.value = ''
  tags.value = []
}

function remove(index: number) {
  const next = [...props.modelValue]
  next.splice(index, 1)
  emit('update:modelValue', next)
}

function onFocus() {
  focused.value = true
  search()
}

function onBlur() {
  // delay to allow click on dropdown
  setTimeout(() => { focused.value = false }, 150)
}
</script>

<template>
  <div class="relative">
    <label class="mb-1.5 block text-xs font-medium text-slate-500">{{ label }}</label>
    <div class="flex flex-wrap items-center gap-1.5 rounded-input border border-slate-300 bg-white px-2.5 py-2 transition-colors" :class="focused ? 'border-brand-500 ring-1 ring-brand-500/20' : ''">
      <span
        v-for="(tag, index) in modelValue"
        :key="`${tag.id}-${tag.name}`"
        class="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700"
      >
        {{ tag.name }}
        <button type="button" class="ml-0.5 grid h-4 w-4 place-items-center rounded-full text-brand-400 hover:bg-brand-200 hover:text-brand-600" @click="remove(index)">×</button>
      </span>
      <input
        v-model="keyword"
        class="min-w-20 flex-1 border-0 bg-transparent py-0.5 text-sm outline-none placeholder:text-slate-400"
        :placeholder="modelValue.length ? '' : placeholder"
        @focus="onFocus"
        @blur="onBlur"
        @input="onInput"
        @keyup.enter.prevent="allowCreate && keyword.trim() ? addNew() : undefined"
      />
    </div>

    <!-- Create hint -->
    <div v-if="allowCreate && keyword.trim() && !tags.some(t => t.name === keyword.trim()) && !modelValue.some(t => t.name === keyword.trim())" class="absolute left-0 right-0 z-20 mt-1 rounded-lg border border-slate-200 bg-white p-2 shadow-card">
      <button class="w-full rounded-btn px-3 py-1.5 text-left text-sm text-brand-600 hover:bg-brand-50" type="button" @mousedown.prevent="addNew">
        创建标签「{{ keyword.trim() }}」
      </button>
    </div>

    <!-- Search results -->
    <div v-if="focused && tags.length" class="absolute left-0 right-0 z-20 mt-1 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-card">
      <button
        v-for="tag in tags"
        :key="tag.id"
        class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50"
        type="button"
        @mousedown.prevent="choose(tag)"
      >
        {{ tag.name }}
      </button>
    </div>

    <p v-if="loading" class="mt-1 text-xs text-slate-400">搜索中…</p>
  </div>
</template>
