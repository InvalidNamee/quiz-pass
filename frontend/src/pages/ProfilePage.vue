<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { changePassword as changePasswordApi, updateProfile } from '../api/v2/users'
import { useAuthStore } from '../stores/auth'
import AppButton from '../components/AppButton.vue'
import { useToast } from '../composables/useToast'

const auth = useAuthStore()
const toast = useToast()
const displayName = ref('')
const bio = ref('')
const avatarSource = ref('default')
const oldPassword = ref('')
const newPassword = ref('')
const showNewPw = ref(false)
const saving = ref(false)
const changingPw = ref(false)

onMounted(() => {
  displayName.value = auth.user?.display_name ?? ''
  bio.value = auth.user?.bio ?? ''
  avatarSource.value = auth.user?.avatar_source ?? 'default'
})

async function save() {
  saving.value = true
  try {
    await updateProfile({ display_name: displayName.value, bio: bio.value, avatar_source: avatarSource.value })
    await auth.loadMe()
    toast.show('资料已保存', 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function changePassword() {
  if (newPassword.value.length < 8) {
    toast.show('新密码至少 8 位', 'error')
    return
  }
  changingPw.value = true
  try {
    await changePasswordApi(oldPassword.value, newPassword.value)
    oldPassword.value = ''
    newPassword.value = ''
    toast.show('密码已更新', 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '密码修改失败', 'error')
  } finally {
    changingPw.value = false
  }
}
</script>

<template>
  <section class="mx-auto grid max-w-3xl gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">账号设置</h1>
      <p class="mt-2 text-slate-600">维护个人资料和登录密码。</p>
    </div>

    <div class="grid gap-5 lg:grid-cols-2">
      <div class="page-card grid gap-4 p-6">
        <h2 class="text-lg font-semibold">个人资料</h2>
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">显示名称</span>
          <input v-model="displayName" class="rounded-input border border-slate-300 bg-white px-3 py-2" />
        </label>
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">简介</span>
          <textarea v-model="bio" class="min-h-24 rounded-input border border-slate-300 bg-white px-3 py-2" />
        </label>
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">头像来源</span>
          <select v-model="avatarSource" class="rounded-input border border-slate-300 bg-white px-3 py-2">
            <option value="default">默认头像（取首字母）</option>
            <option value="qq_email">QQ 邮箱头像</option>
            <option value="manual">手动设置 URL</option>
          </select>
        </label>
        <AppButton :loading="saving" @click="save">保存资料</AppButton>
      </div>

      <div class="page-card grid content-start gap-4 p-6">
        <h2 class="text-lg font-semibold">修改密码</h2>
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">当前密码</span>
          <input v-model="oldPassword" class="rounded-input border border-slate-300 bg-white px-3 py-2" type="password" autocomplete="current-password" />
        </label>
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">新密码（至少 8 位）</span>
          <div class="relative">
            <input v-model="newPassword" class="w-full rounded-input border border-slate-300 bg-white py-2 pl-3 pr-10" :type="showNewPw ? 'text' : 'password'" autocomplete="new-password" />
            <button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" @click="showNewPw = !showNewPw">
              <svg v-if="showNewPw" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M15 12a3 3 0 01-3 3m0 0a3 3 0 01-3-3m3 3V9" /></svg>
              <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
            </button>
          </div>
        </label>
        <AppButton variant="secondary" :loading="changingPw" @click="changePassword">更新密码</AppButton>
      </div>
    </div>
  </section>
</template>
