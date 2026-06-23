<script setup lang="ts">
import { ref } from 'vue'
import { searchUsers } from '../api/v2/users'
import type { UserPublic } from '../api/types'
import UserAvatar from './UserAvatar.vue'
import { isUtilityWindowSupported } from '../features/utility-windows/utilityWindow'
import { openAuthorFilterWindow } from '../features/utility-windows/openUtilityFlows'

const props = defineProps<{ modelValue: UserPublic | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: UserPublic | null] }>()

const dialogVisible = ref(false)
const keyword = ref('')
const searchResults = ref<UserPublic[]>([])
const selectedUserId = ref<number | null>(null)
let pendingWindowListener: ((event: Event) => void) | null = null

async function search() {
  const k = keyword.value.trim()
  if (!k) return
  try {
    const data = await searchUsers({ keyword: k, page: 1 })
    searchResults.value = data.items
  } catch {
    searchResults.value = []
  }
}

function openDialog() {
  if (isUtilityWindowSupported()) {
    if (pendingWindowListener) window.removeEventListener('quiz-pass:utility-window-completed', pendingWindowListener)
    openAuthorFilterWindow({ selectedUser: props.modelValue }).then((opened) => {
      pendingWindowListener = (event: Event) => {
        const detail = (event as CustomEvent<{ kind?: string; requestId?: string; action?: string; result?: { user?: UserPublic | null } }>).detail
        if (detail?.kind !== 'author-filter' || detail.requestId !== opened.requestId || detail.action !== 'author-selected') return
        emit('update:modelValue', detail.result?.user ?? null)
        window.removeEventListener('quiz-pass:utility-window-completed', pendingWindowListener!)
        pendingWindowListener = null
      }
      window.addEventListener('quiz-pass:utility-window-completed', pendingWindowListener)
    }).catch(() => {
      keyword.value = ''
      searchResults.value = []
      selectedUserId.value = props.modelValue?.id ?? null
      dialogVisible.value = true
    })
    return
  }
  keyword.value = ''
  searchResults.value = []
  selectedUserId.value = props.modelValue?.id ?? null
  dialogVisible.value = true
}

function selectUser(id: number) {
  selectedUserId.value = selectedUserId.value === id ? null : id
}

function confirm() {
  const user = selectedUserId.value
    ? searchResults.value.find(u => u.id === selectedUserId.value) ?? null
    : null
  dialogVisible.value = false
  emit('update:modelValue', user)
}
</script>

<template>
  <el-button size="small" @click="openDialog">{{ modelValue ? '作者(已选)' : '作者' }}</el-button>

  <el-dialog v-model="dialogVisible" title="选择作者" width="420px">
    <div class="mb-3 flex gap-2">
      <el-input v-model="keyword" placeholder="搜索用户" clearable @keyup.enter="search" @clear="searchResults = []" />
      <el-button @click="search">搜索</el-button>
    </div>
    <div class="flex max-h-80 flex-col gap-1 overflow-y-auto">
      <div
        v-for="user in searchResults"
        :key="user.id"
        class="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5"
        :class="selectedUserId === user.id ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-slate-50'"
        @click="selectUser(user.id)"
      >
        <UserAvatar :src="user.avatar_url" :name="user.display_name || user.username" :size="28" />
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium text-slate-800">{{ user.display_name || user.username }}</div>
          <div class="truncate text-xs text-slate-400">
            <template v-if="user.display_name">@{{ user.username }}</template>
            <template v-else>#{{ user.id }}</template>
          </div>
        </div>
        <span class="shrink-0 text-xs text-slate-400">#{{ user.id }}</span>
      </div>
    </div>
    <p v-if="!searchResults.length && keyword.trim()" class="py-4 text-center text-sm text-slate-400">未找到用户</p>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :disabled="!selectedUserId" @click="confirm">确定</el-button>
    </template>
  </el-dialog>
</template>
