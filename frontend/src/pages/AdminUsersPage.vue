<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page, type UserMe } from '../api/client'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppPagination from '../components/AppPagination.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'

const route = useRoute()
const router = useRouter()
const users = ref<UserMe[]>([])
const keyword = ref('')
const role = ref('')
const isActive = ref('')
const pageInfo = ref<Page<UserMe> | null>(null)
const loading = ref(true)

async function load() {
  keyword.value = String(route.query.keyword || '')
  role.value = String(route.query.role || '')
  isActive.value = String(route.query.is_active || '')
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (keyword.value) params.set('keyword', keyword.value)
  if (role.value) params.set('role', role.value)
  if (isActive.value) params.set('is_active', isActive.value)
  loading.value = true
  try {
    const data = await api<Page<UserMe>>(`/api/v1/admin/users?${params}`)
    pageInfo.value = data
    users.value = data.items
  } finally {
    loading.value = false
  }
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
  <section class="grid gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">用户管理</h1>
      <div class="mt-5 grid max-w-3xl gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <input v-model="keyword" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="搜索用户" />
        <select v-model="role" class="rounded-input border border-slate-300 bg-white px-3 py-2">
          <option value="">全部角色</option>
          <option value="user">user</option>
          <option value="admin">admin</option>
        </select>
        <select v-model="isActive" class="rounded-input border border-slate-300 bg-white px-3 py-2">
          <option value="">全部状态</option>
          <option value="true">启用</option>
          <option value="false">禁用</option>
        </select>
        <AppButton variant="secondary" @click="applyFilters()">筛选</AppButton>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!users.length" title="没有匹配的用户" />

    <template v-else>
      <div class="grid gap-3">
        <RouterLink v-for="user in users" :key="user.id" class="page-card flex items-center justify-between gap-4 p-4 hover:border-brand-500/30" :to="`/users/${user.id}`">
          <div>
            <strong>{{ user.username }}</strong>
            <span class="ml-2 text-sm text-slate-500">{{ user.email }}</span>
          </div>
          <div class="flex items-center gap-2">
            <AppBadge :variant="user.role === 'admin' ? 'info' : 'default'">{{ user.role }}</AppBadge>
            <AppBadge :variant="user.is_active ? 'success' : 'danger'">{{ user.is_active ? '启用' : '禁用' }}</AppBadge>
          </div>
        </RouterLink>
      </div>

      <AppPagination
        v-if="pageInfo"
        :page="pageInfo.page"
        :total-pages="pageInfo.total_pages || 1"
        :total="pageInfo.total"
        @update:page="applyFilters"
      />
    </template>
  </section>
</template>
