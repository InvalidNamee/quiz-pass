<script setup lang="ts">
import { ref } from 'vue'
import type { UserMe } from '../../api/types'
import { updateAdminUser } from '../../api/v2/users'
import { useAuthStore } from '../../stores/auth'
import { useToast } from '../../composables/useToast'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  user?: UserMe
  requestId?: string
}

const auth = useAuthStore()
const toast = useToast()
const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('admin-user-edit')
const user = payload.value.user
const saving = ref(false)
const editForm = ref({
  display_name: user?.display_name || '',
  bio: user?.bio || '',
  is_active: user?.is_active ?? true,
})

async function saveUser() {
  if (!user) return
  saving.value = true
  try {
    const updated = await updateAdminUser(user.id, {
      display_name: editForm.value.display_name || null,
      bio: editForm.value.bio || null,
      is_active: editForm.value.is_active,
    })
    toast.show('用户信息已更新', 'success')
    if (auth.user?.id === user.id) await auth.loadMe()
    await complete('admin-user-updated', { user: updated })
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '更新失败', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="min-h-screen bg-white p-4 text-slate-700">
    <div v-if="user" class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">编辑用户</h1>
        <p class="mt-1 text-sm text-slate-500">{{ user.display_name || user.username }} · #{{ user.id }}</p>
      </div>

      <div>
        <p class="mb-1 text-sm font-medium text-slate-700">显示名</p>
        <el-input v-model="editForm.display_name" placeholder="可留空" />
      </div>
      <div>
        <p class="mb-1 text-sm font-medium text-slate-700">简介</p>
        <el-input v-model="editForm.bio" type="textarea" :rows="4" placeholder="可留空" />
      </div>
      <el-checkbox v-model="editForm.is_active" :disabled="user.id === auth.user?.id">启用账号</el-checkbox>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </div>
    </div>
    <p v-else class="p-4 text-sm text-slate-500">缺少用户信息。</p>
  </section>
</template>
