<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { changePassword as changePasswordApi, updateProfile } from '../api/v2/users'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

const auth = useAuthStore()
const toast = useToast()
const displayName = ref('')
const bio = ref('')
const avatarSource = ref('default')
const avatarUrl = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const showNewPw = ref(false)
const saving = ref(false)
const changingPw = ref(false)

onMounted(() => {
  displayName.value = auth.user?.display_name ?? ''
  bio.value = auth.user?.bio ?? ''
  avatarSource.value = auth.user?.avatar_source ?? 'default'
  avatarUrl.value = auth.user?.avatar_url ?? ''
})

async function save() {
  saving.value = true
  try {
    await updateProfile({
      display_name: displayName.value,
      bio: bio.value,
      avatar_source: avatarSource.value,
      avatar_url: avatarSource.value === 'manual' ? avatarUrl.value.trim() || null : null,
    })
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
  <section class="qp-page mx-auto max-w-3xl">
    <div class="qp-titlebar">
      <div>
      <h1 class="qp-title">账号设置</h1>
      <p class="qp-subtitle">维护个人资料和登录密码。</p>
      </div>
    </div>

    <div class="grid gap-3 lg:grid-cols-2">
      <el-form class="qp-section" label-position="top">
        <h2 class="qp-section-title">个人资料</h2>
        <el-form-item label="显示名称"><el-input v-model="displayName" /></el-form-item>
        <el-form-item label="简介"><el-input v-model="bio" type="textarea" :rows="5" /></el-form-item>
        <el-form-item label="头像来源">
          <el-select v-model="avatarSource" class="w-full">
            <el-option value="default" label="默认头像（取首字母）" />
            <el-option value="qq_email" label="QQ 邮箱头像" />
            <el-option value="manual" label="手动设置 URL" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="avatarSource === 'manual'" label="头像 URL">
          <el-input v-model="avatarUrl" placeholder="https://example.com/avatar.png" />
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="save">保存资料</el-button>
      </el-form>

      <el-form class="qp-section content-start" label-position="top">
        <h2 class="qp-section-title">修改密码</h2>
        <el-form-item label="当前密码"><el-input v-model="oldPassword" type="password" show-password autocomplete="current-password" /></el-form-item>
        <el-form-item label="新密码（至少 8 位）"><el-input v-model="newPassword" type="password" show-password autocomplete="new-password" /></el-form-item>
        <el-button :loading="changingPw" @click="changePassword">更新密码</el-button>
      </el-form>
    </div>
  </section>
</template>
