<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type Page, type UserMe } from '../api/client'

const users = ref<UserMe[]>([])
const keyword = ref('')
const role = ref('')
const isActive = ref('')

async function load() {
  const params = new URLSearchParams()
  if (keyword.value) params.set('keyword', keyword.value)
  if (role.value) params.set('role', role.value)
  if (isActive.value) params.set('is_active', isActive.value)
  const data = await api<Page<UserMe>>(`/api/v1/admin/users?${params}`)
  users.value = data.items
}

onMounted(load)
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
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="load">筛选</button>
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
  </section>
</template>
