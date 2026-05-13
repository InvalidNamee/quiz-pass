<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page, type UserMe } from '../api/client'
import { useAuthStore } from '../stores/auth'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppPagination from '../components/AppPagination.vue'
import AppLoading from '../components/AppLoading.vue'
import AppEmpty from '../components/AppEmpty.vue'
import AppModal from '../components/AppModal.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const users = ref<UserMe[]>([])
const keyword = ref('')
const role = ref('')
const isActive = ref('')
const pageInfo = ref<Page<UserMe> | null>(null)
const loading = ref(true)
const editingUser = ref<UserMe | null>(null)
const editForm = ref({ display_name: '', bio: '', is_active: true })
const savingUser = ref(false)
const resettingUserId = ref<number | null>(null)
const temporaryPassword = ref('')

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

function startEdit(user: UserMe) {
  editingUser.value = user
  editForm.value = {
    display_name: user.display_name || '',
    bio: user.bio || '',
    is_active: user.is_active,
  }
}

async function saveUser() {
  if (!editingUser.value) return
  const editingUserId = editingUser.value.id
  savingUser.value = true
  try {
    await api<UserMe>(`/api/v1/admin/users/${editingUserId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        display_name: editForm.value.display_name || null,
        bio: editForm.value.bio || null,
        is_active: editForm.value.is_active,
      }),
    })
    toast.show('用户信息已更新', 'success')
    editingUser.value = null
    await load()
    if (auth.user?.id === editingUserId) await auth.loadMe()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '更新失败', 'error')
  } finally {
    savingUser.value = false
  }
}

function closeEditModal(open: boolean) {
  if (!open) editingUser.value = null
}

function closePasswordModal(open: boolean) {
  if (!open) temporaryPassword.value = ''
}

async function toggleActive(user: UserMe) {
  try {
    await api<UserMe>(`/api/v1/admin/users/${user.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: !user.is_active }),
    })
    toast.show(user.is_active ? '用户已禁用' : '用户已启用', 'success')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '操作失败', 'error')
  }
}

async function resetPassword(user: UserMe) {
  resettingUserId.value = user.id
  try {
    const data = await api<{ temporary_password: string }>(`/api/v1/admin/users/${user.id}/reset-password`, { method: 'POST' })
    temporaryPassword.value = data.temporary_password
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '重置失败', 'error')
  } finally {
    resettingUserId.value = null
  }
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
        <article v-for="user in users" :key="user.id" class="page-card flex flex-wrap items-center justify-between gap-4 p-4">
          <RouterLink class="min-w-0 hover:text-brand-600" :to="`/users/${user.id}`">
            <div class="flex min-w-0 flex-wrap items-center gap-2">
              <strong class="truncate">{{ user.display_name || user.username }}</strong>
              <span class="text-sm text-slate-500">@{{ user.username }}</span>
            </div>
            <p class="mt-1 truncate text-sm text-slate-500">{{ user.email }}</p>
          </RouterLink>
          <div class="flex flex-wrap items-center justify-end gap-2">
            <AppBadge :variant="user.role === 'admin' ? 'info' : 'default'">{{ user.role }}</AppBadge>
            <AppBadge :variant="user.is_active ? 'success' : 'danger'">{{ user.is_active ? '启用' : '禁用' }}</AppBadge>
            <AppButton variant="ghost" size="sm" @click="startEdit(user)">编辑</AppButton>
            <AppButton
              variant="secondary"
              size="sm"
              :disabled="user.id === auth.user?.id"
              @click="toggleActive(user)"
            >{{ user.is_active ? '禁用' : '启用' }}</AppButton>
            <AppButton
              variant="danger"
              size="sm"
              :disabled="user.id === auth.user?.id"
              :loading="resettingUserId === user.id"
              @click="resetPassword(user)"
            >重置密码</AppButton>
          </div>
        </article>
      </div>

      <AppPagination
        v-if="pageInfo"
        :page="pageInfo.page"
        :total-pages="pageInfo.total_pages || 1"
        :total="pageInfo.total"
        @update:page="applyFilters"
      />
    </template>

    <AppModal :model-value="!!editingUser" title="编辑用户" @update:model-value="closeEditModal">
      <div class="grid gap-4">
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">显示名</span>
          <input v-model="editForm.display_name" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="可留空" />
        </label>
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">简介</span>
          <textarea v-model="editForm.bio" class="min-h-24 rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="可留空" />
        </label>
        <label class="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          <input v-model="editForm.is_active" type="checkbox" class="rounded" :disabled="editingUser?.id === auth.user?.id" />
          启用账号
        </label>
      </div>
      <template #footer>
        <AppButton variant="ghost" @click="editingUser = null">取消</AppButton>
        <AppButton :loading="savingUser" @click="saveUser">保存</AppButton>
      </template>
    </AppModal>

    <AppModal :model-value="!!temporaryPassword" title="临时密码" @update:model-value="closePasswordModal">
      <div class="grid gap-3">
        <p class="text-sm text-slate-600">请立即把这个临时密码交给用户。关闭后前端不会再显示。</p>
        <code class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-base font-semibold text-slate-900">{{ temporaryPassword }}</code>
      </div>
      <template #footer>
        <AppButton @click="temporaryPassword = ''">我已记录</AppButton>
      </template>
    </AppModal>
  </section>
</template>
