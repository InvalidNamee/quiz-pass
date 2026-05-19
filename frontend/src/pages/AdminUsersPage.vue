<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Page, UserMe } from '../api/types'
import { listAdminUsers, resetAdminPassword, updateAdminUser } from '../api/v2/users'
import { useAuthStore } from '../stores/auth'
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
  loading.value = true
  try {
    const data = await listAdminUsers({
      page: Number(route.query.page || 1),
      keyword: keyword.value || undefined,
      role: role.value || undefined,
      is_active: isActive.value || undefined,
    })
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
    await updateAdminUser(editingUserId, {
      display_name: editForm.value.display_name || null,
      bio: editForm.value.bio || null,
      is_active: editForm.value.is_active,
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
    await updateAdminUser(user.id, { is_active: !user.is_active })
    toast.show(user.is_active ? '用户已禁用' : '用户已启用', 'success')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '操作失败', 'error')
  }
}

async function resetPassword(user: UserMe) {
  resettingUserId.value = user.id
  try {
    const data = await resetAdminPassword(user.id)
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
  <section class="qp-page">
    <div class="qp-titlebar">
      <h1 class="qp-title">用户管理</h1>
    </div>
    <div class="qp-toolbar">
      <el-input v-model="keyword" size="small" placeholder="搜索用户" clearable style="width: 200px" />
      <el-select v-model="role" size="small" placeholder="全部角色" style="width: 120px">
        <el-option value="">全部角色</el-option>
        <el-option value="user">user</el-option>
        <el-option value="admin">admin</el-option>
      </el-select>
      <el-select v-model="isActive" size="small" placeholder="全部状态" style="width: 120px">
        <el-option value="">全部状态</el-option>
        <el-option value="true">启用</el-option>
        <el-option value="false">禁用</el-option>
      </el-select>
      <el-button size="small" type="primary" @click="applyFilters()">筛选</el-button>
    </div>

    <el-table v-loading="loading" :data="users" size="small" empty-text="没有匹配的用户">
      <el-table-column label="用户" min-width="220">
        <template #default="{ row }">
          <RouterLink :to="`/users/${row.id}`" class="hover:text-brand-600">
            <div class="flex flex-wrap items-center gap-2">
              <strong class="truncate">{{ row.display_name || row.username }}</strong>
              <span class="text-sm text-slate-500">@{{ row.username }}</span>
            </div>
            <p class="truncate text-sm text-slate-500">{{ row.email }}</p>
          </RouterLink>
        </template>
      </el-table-column>
      <el-table-column label="角色" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.role === 'admin'" type="info">{{ row.role }}</el-tag>
          <el-tag v-else>{{ row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="300">
        <template #default="{ row }">
          <el-button text size="small" @click="startEdit(row)">编辑</el-button>
          <el-button
            size="small"
            :disabled="row.id === auth.user?.id"
            @click="toggleActive(row)"
          >{{ row.is_active ? '禁用' : '启用' }}</el-button>
          <el-button
            text
            size="small"
            type="danger"
            :disabled="row.id === auth.user?.id"
            :loading="resettingUserId === row.id"
            @click="resetPassword(row)"
          >重置密码</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="pageInfo"
      background
      size="small"
      :current-page="pageInfo.page"
      :page-count="pageInfo.total_pages || 1"
      :total="pageInfo.total"
      layout="prev, pager, next, total"
      @current-change="applyFilters"
    />

    <el-dialog :model-value="!!editingUser" title="编辑用户" @update:model-value="closeEditModal">
      <div class="grid gap-4">
        <div>
          <p class="mb-1 text-sm font-medium text-slate-700">显示名</p>
          <el-input v-model="editForm.display_name" placeholder="可留空" />
        </div>
        <div>
          <p class="mb-1 text-sm font-medium text-slate-700">简介</p>
          <el-input v-model="editForm.bio" type="textarea" :rows="4" placeholder="可留空" />
        </div>
        <el-checkbox v-model="editForm.is_active" :disabled="editingUser?.id === auth.user?.id">启用账号</el-checkbox>
      </div>
      <template #footer>
        <el-button @click="editingUser = null">取消</el-button>
        <el-button type="primary" :loading="savingUser" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog :model-value="!!temporaryPassword" title="临时密码" @update:model-value="closePasswordModal">
      <div class="grid gap-3">
        <p class="text-sm text-slate-600">请立即把这个临时密码交给用户。关闭后前端不会再显示。</p>
        <code class="border border-slate-200 bg-slate-50 px-3 py-2 text-base font-semibold text-slate-900">{{ temporaryPassword }}</code>
      </div>
      <template #footer>
        <el-button type="primary" @click="temporaryPassword = ''">我已记录</el-button>
      </template>
    </el-dialog>
  </section>
</template>
