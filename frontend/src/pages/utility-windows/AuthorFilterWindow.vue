<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { searchUsers } from '../../api/v2/users'
import type { UserPublic } from '../../api/types'
import UserAvatar from '../../components/UserAvatar.vue'
import { useToast } from '../../composables/useToast'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  selectedUser?: UserPublic | null
  requestId?: string
}

const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('author-filter')
const keyword = ref('')
const searchResults = ref<UserPublic[]>([])
const selectedUserId = ref<number | null>(null)
const loading = ref(false)

async function search() {
  const value = keyword.value.trim()
  if (!value) {
    searchResults.value = []
    return
  }
  loading.value = true
  try {
    searchResults.value = (await searchUsers({ keyword: value, page: 1 })).items
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '搜索用户失败', 'error')
    searchResults.value = []
  } finally {
    loading.value = false
  }
}

function selectUser(id: number) {
  selectedUserId.value = selectedUserId.value === id ? null : id
}

function selectedUser() {
  if (!selectedUserId.value) return null
  return searchResults.value.find((user) => user.id === selectedUserId.value) ?? payload.value.selectedUser ?? null
}

function confirm() {
  complete('author-selected', { user: selectedUser() })
}

function clearSelection() {
  complete('author-selected', { user: null })
}

onMounted(() => {
  const user = payload.value.selectedUser
  if (user) {
    selectedUserId.value = user.id
    keyword.value = user.username
    searchResults.value = [user]
  }
})
</script>

<template>
  <section class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">选择作者</h1>
        <p class="mt-1 text-sm text-slate-500">按用户 ID、用户名或显示名搜索作者。</p>
      </div>

      <div class="flex gap-2">
        <el-input v-model="keyword" placeholder="搜索用户" clearable @keyup.enter="search" @clear="searchResults = []" />
        <el-button @click="search">搜索</el-button>
      </div>

      <div v-loading="loading" class="flex max-h-80 min-h-32 flex-col gap-1 overflow-y-auto rounded-md border border-slate-200 p-2">
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
        <p v-if="!searchResults.length && keyword.trim() && !loading" class="py-6 text-center text-sm text-slate-400">未找到用户</p>
      </div>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">取消</el-button>
        <el-button @click="clearSelection">清除</el-button>
        <el-button type="primary" :disabled="!selectedUserId" @click="confirm">确定</el-button>
      </div>
    </div>
  </section>
</template>
