<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page, type UserMe } from '../api/client'

const route = useRoute()
const router = useRouter()
const users = ref<UserMe[]>([])
const keyword = ref('')
const role = ref('')
const isActive = ref('')
const pageInfo = ref<Page<UserMe> | null>(null)

async function load() {
  keyword.value = String(route.query.keyword || '')
  role.value = String(route.query.role || '')
  isActive.value = String(route.query.is_active || '')
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (keyword.value) params.set('keyword', keyword.value)
  if (role.value) params.set('role', role.value)
  if (isActive.value) params.set('is_active', isActive.value)
  const data = await api<Page<UserMe>>(`/api/v1/admin/users?${params}`)
  pageInfo.value = data
  users.value = data.items
}

function applyFilters(page = 1) {
  const query: Record<string, string> = {}
  if (page > 1) query.page = String(page)
  if (keyword.value) query.keyword = keyword.value
  if (role.value) query.role = role.value
  if (isActive.value) query.is_active = isActive.value
  router.push({ query })
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">用户管理</h1>
    <div class="my-4 grid max-w-3xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <input v-model="keyword" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="邮箱、用户名、显示名" />
      <select v-model="role" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="">全部角色</option>
        <option value="user">user</option>
        <option value="admin">admin</option>
      </select>
      <select v-model="isActive" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="">全部状态</option>
        <option value="true">启用</option>
        <option value="false">禁用</option>
      </select>
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="applyFilters()">筛选</button>
    </div>
    <div class="mt-4 grid gap-3">
      <RouterLink v-for="user in users" :key="user.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-blue-300" :to="`/users/${user.id}`">
        <div>
          <strong>{{ user.username }}</strong>
          <span class="block text-sm text-slate-500">{{ user.email }}</span>
        </div>
        <span class="text-sm text-slate-500">{{ user.role }} · {{ user.is_active ? '启用' : '禁用' }}</span>
      </RouterLink>
    </div>
    <div v-if="pageInfo" class="mt-4 flex items-center justify-end gap-3 text-sm text-slate-600">
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page <= 1" @click="applyFilters(pageInfo.page - 1)">上一页</button>
      <span>第 {{ pageInfo.page }} / {{ pageInfo.total_pages || 1 }} 页，共 {{ pageInfo.total }} 个</span>
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page >= pageInfo.total_pages" @click="applyFilters(pageInfo.page + 1)">下一页</button>
    </div>
  </section>
</template>
