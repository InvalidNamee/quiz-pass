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
  <div class="relative flex min-h-[85vh] items-center justify-center overflow-hidden px-4">
    <!-- Decorative background glow spheres -->
    <div class="absolute -top-40 -left-40 h-80 w-80 rounded-full bg-indigo-400/20 blur-3xl" />
    <div class="absolute -bottom-40 -right-40 h-80 w-80 rounded-full bg-purple-400/20 blur-3xl" />

    <el-form
      class="relative z-10 w-full max-w-sm rounded-2xl border border-white/40 bg-white/70 p-6 shadow-2xl backdrop-blur-xl transition-all duration-300 hover:shadow-indigo-500/5"
      label-position="top"
      @submit.prevent
    >
      <div class="mb-6 text-center">
        <div class="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/25">
          <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h1 class="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent">Quiz Pass</h1>
        <p class="mt-1 text-xs text-slate-400">AI 智能题库生成与练习平台</p>
      </div>

      <el-form-item label="用户名或邮箱">
        <el-input v-model="identifier" placeholder="请输入用户名或邮箱" autocomplete="username" @keyup.enter="submit" />
      </el-form-item>

      <el-form-item label="密码">
        <el-input v-model="password" type="password" placeholder="请输入密码" autocomplete="current-password" show-password @keyup.enter="submit" />
      </el-form-item>

      <el-button
        type="primary"
        :loading="loading"
        class="w-full !rounded-xl !h-10 !bg-gradient-to-r !from-indigo-500 !to-purple-500 border-none shadow-md hover:shadow-indigo-500/20 active:scale-98 transition-all"
        @click="submit"
      >
        立即登录
      </el-button>

      <div class="mt-4 flex items-center justify-between text-xs font-medium">
        <router-link to="/forgot-password" class="text-indigo-600 hover:text-indigo-500 transition-colors">忘记密码？</router-link>
        <span class="text-slate-400">还没有账号？<router-link to="/register" class="text-indigo-600 hover:text-indigo-500 transition-colors">注册</router-link></span>
      </div>

      <el-alert v-if="needsVerification" class="mt-4 !rounded-xl" type="warning" :closable="false" show-icon title="请先验证邮箱">
        <div class="mt-2 flex gap-2">
          <el-input v-model="verificationEmail" placeholder="注册邮箱" size="small" />
          <el-button size="small" :loading="resendLoading" @click="resend">重发</el-button>
        </div>
      </el-alert>
    </el-form>
  </div>
</template>
