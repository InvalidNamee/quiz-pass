<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'
import { resendVerification } from '../api/v2/auth'
import { useToast } from '../composables/useToast'

const email = ref(''); const username = ref(''); const password = ref(''); const loading = ref(false)
const successMessage = ref('')
const resendLoading = ref(false)
const auth = useAuthStore()
const toast = useToast()

async function submit() {
  const cleanEmail = email.value.trim(); const cleanUsername = username.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) { toast.show('请输入正确的邮箱地址', 'error'); return }
  if (cleanUsername.length < 3) { toast.show('用户名至少 3 位', 'error'); return }
  if (password.value.length < 8) { toast.show('密码至少 8 位', 'error'); return }
  loading.value = true
  try {
    const result = await auth.register(cleanEmail, cleanUsername, password.value)
    successMessage.value = result.message || '验证邮件已发送，请查收邮箱完成验证'
    toast.show(successMessage.value, 'success')
  }
  catch (e) { toast.show(e instanceof Error ? e.message : '注册失败', 'error') }
  finally { loading.value = false }
}

async function resend() {
  const cleanEmail = email.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) { toast.show('请输入正确的邮箱地址', 'error'); return }
  resendLoading.value = true
  try {
    const result = await resendVerification(cleanEmail)
    toast.show(result.message || '验证邮件已重新发送', 'success')
  } catch (e) {
    toast.show(e instanceof Error ? e.message : '发送失败', 'error')
  } finally {
    resendLoading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-[80vh] items-center justify-center">
    <el-form class="w-full max-w-sm border border-slate-200 bg-white p-5" label-position="top" @submit.prevent>
      <h1 class="mb-4 text-center text-lg font-semibold text-slate-900">创建账号</h1>
      <el-form-item label="邮箱"><el-input v-model="email" autocomplete="email" /></el-form-item>
      <el-form-item label="用户名"><el-input v-model="username" autocomplete="username" placeholder="至少 3 位" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="password" type="password" autocomplete="new-password" placeholder="至少 8 位" show-password /></el-form-item>
      <el-button type="primary" :loading="loading" class="w-full" @click="submit">注册</el-button>
      <el-alert v-if="successMessage" class="mt-4" type="success" :closable="false" show-icon>
        <template #title>{{ successMessage }}</template>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <el-button size="small" :loading="resendLoading" @click="resend">重新发送验证邮件</el-button>
          <router-link to="/login" class="text-blue-600">去登录</router-link>
        </div>
      </el-alert>
      <p class="mt-4 text-center text-sm text-slate-500">已有账号？<router-link to="/login" class="text-blue-600">登录</router-link></p>
    </el-form>
  </div>
</template>
