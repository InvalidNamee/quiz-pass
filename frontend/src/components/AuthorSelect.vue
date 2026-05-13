<script setup lang="ts">
import { ref, watch } from 'vue'
import { api, type Page, type UserPublic } from '../api/client'

const props = defineProps<{
  modelValue: number | null
  label?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number | null]
}>()

const keyword = ref('')
const users = ref<UserPublic[]>([])
const selected = ref<UserPublic | null>(null)
const loading = ref(false)

async function search() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('page_size', '8')
    if (keyword.value.trim()) params.set('keyword', keyword.value.trim())
    users.value = (await api<Page<UserPublic>>(`/api/v1/users/search?${params}`)).items
  } finally {
    loading.value = false
  }
}

function choose(user: UserPublic) {
  selected.value = user
  keyword.value = user.display_name || user.username
  users.value = []
  emit('update:modelValue', user.id)
}

function clear() {
  selected.value = null
  keyword.value = ''
  users.value = []
  emit('update:modelValue', null)
}

watch(
  () => props.modelValue,
  async (value) => {
    if (!value) {
      selected.value = null
      keyword.value = ''
      return
    }
    if (selected.value?.id !== value) {
      const user = await api<UserPublic>(`/api/v1/users/${value}`)
      selected.value = user
      keyword.value = user.display_name || user.username
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="relative">
    <label class="mb-1 block text-xs font-medium text-slate-500">{{ label || '作者' }}</label>
    <div class="flex gap-2">
      <input v-model="keyword" class="min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="搜索作者" @keyup.enter="search" />
      <button class="rounded-md bg-slate-200 px-3 py-2 text-sm text-slate-900" type="button" @click="search">{{ loading ? '搜索中' : '搜索' }}</button>
      <button v-if="modelValue" class="rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-600" type="button" @click="clear">清空</button>
    </div>
    <div v-if="users.length" class="absolute left-0 right-0 z-10 mt-2 overflow-hidden rounded-lg border border-slate-200 bg-white">
      <button
        v-for="user in users"
        :key="user.id"
        class="grid w-full grid-cols-[32px_1fr_auto] items-center gap-3 px-3 py-2 text-left hover:bg-blue-50"
        type="button"
        @click="choose(user)"
      >
        <img v-if="user.avatar_url" class="h-8 w-8 rounded-full object-cover" :src="user.avatar_url" alt="" />
        <span v-else class="grid h-8 w-8 place-items-center rounded-full bg-slate-800 text-xs font-bold text-white">{{ (user.display_name || user.username).slice(0, 1).toUpperCase() }}</span>
        <span class="min-w-0">
          <strong class="block truncate text-sm">{{ user.display_name || user.username }}</strong>
          <span class="block truncate text-xs text-slate-500">@{{ user.username }}</span>
        </span>
        <span class="text-xs text-slate-500">{{ user.public_bank_count }} 题库</span>
      </button>
    </div>
  </div>
</template>
