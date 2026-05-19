<script setup lang="ts">
import { ref, watch } from 'vue'
import { searchUsers, getUserPublic } from '../api/v2/users'
import type { UserPublic } from '../api/types'

const props = defineProps<{ modelValue: number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: number | null] }>()

const keyword = ref('')
const users = ref<UserPublic[]>([])
const selected = ref<UserPublic | null>(null)
const focused = ref(false)
let timer: ReturnType<typeof setTimeout>

async function search() {
  if (!keyword.value.trim()) { users.value = []; return }
  users.value = (await searchUsers({ page: 1, keyword: keyword.value.trim() })).items.slice(0, 5)
}

function onInput() { clearTimeout(timer); timer = setTimeout(search, 200) }

function choose(user: UserPublic) {
  selected.value = user
  keyword.value = user.display_name || user.username
  users.value = []
  focused.value = false
  emit('update:modelValue', user.id)
}

function clear() {
  selected.value = null; keyword.value = ''; users.value = []
  emit('update:modelValue', null)
}

watch(() => props.modelValue, async (v) => {
  if (!v) { selected.value = null; keyword.value = ''; return }
  if (selected.value?.id !== v) {
    const user = await getUserPublic(v)
    selected.value = user; keyword.value = user.display_name || user.username
  }
}, { immediate: true })
</script>

<template>
  <div class="relative">
    <div class="flex items-center gap-1">
      <input v-model="keyword" class="w-32 rounded-input border border-slate-300 bg-white px-2 py-1.5 text-sm" placeholder="作者" @focus="focused = true" @blur="focused = false" @input="onInput" @keyup.enter="search" />
      <button v-if="modelValue" class="text-xs text-slate-400 hover:text-slate-600" @click="clear">×</button>
    </div>
    <div v-if="focused && users.length" class="absolute left-0 top-full z-20 mt-1 w-48 rounded-lg border border-slate-200 bg-white shadow-modal">
      <button v-for="user in users" :key="user.id" class="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50" @mousedown.prevent="choose(user)">
        <span class="truncate">{{ user.display_name || user.username }}</span>
        <span class="text-xs text-slate-400">{{ user.public_bank_count }} 题库</span>
      </button>
    </div>
  </div>
</template>
