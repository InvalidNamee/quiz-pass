<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { resendVerification } from '../api/v2/auth'
import { useToast } from '../composables/useToast'

const identifier = ref(''); const password = ref(''); const loading = ref(false)
const needsVerification = ref(false)
const verificationEmail = ref('')
const resendLoading = ref(false)
const auth = useAuthStore(); const router = useRouter()
const toast = useToast()

async function submit() {
  loading.value = true
  needsVerification.value = false
  try { await auth.login(identifier.value.trim(), password.value); router.push('/dashboard') }
  catch (e) {
    const message = e instanceof Error ? e.message : '登录失败'
    if (message.includes('验证邮箱')) {
      needsVerification.value = true
      verificationEmail.value = identifier.value.includes('@') ? identifier.value.trim() : ''
    }
    toast.show(message, 'error')
  }
  finally { loading.value = false }
}

async function resend() {
  const email = verificationEmail.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { toast.show('请输入注册邮箱后再重发验证邮件', 'error'); return }
  resendLoading.value = true
  try {
    const result = await resendVerification(email)
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
      <h1 class="mb-4 text-center text-lg font-semibold text-slate-900">Quiz Pass</h1>
      <el-form-item label="用户名或邮箱"><el-input v-model="identifier" autocomplete="username" @keyup.enter="submit" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="password" type="password" autocomplete="current-password" show-password @keyup.enter="submit" /></el-form-item>
      <el-button type="primary" :loading="loading" class="w-full" @click="submit">登录</el-button>
      <div class="mt-3 flex items-center justify-between text-sm">
        <router-link to="/forgot-password" class="text-blue-600">忘记密码？</router-link>
        <span class="text-slate-500">还没有账号？<router-link to="/register" class="text-blue-600">注册</router-link></span>
      </div>
      <el-alert v-if="needsVerification" class="mt-4" type="warning" :closable="false" show-icon title="请先验证邮箱">
        <div class="mt-2 flex gap-2">
          <el-input v-model="verificationEmail" placeholder="注册邮箱" size="small" />
          <el-button size="small" :loading="resendLoading" @click="resend">重发</el-button>
        </div>
      </el-alert>
    </el-form>
  </div>
</template>
