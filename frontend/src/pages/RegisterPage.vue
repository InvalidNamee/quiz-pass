<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppButton from '../components/AppButton.vue'

const email = ref('')
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const showPw = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  const cleanEmail = email.value.trim()
  const cleanUsername = username.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
    error.value = '请输入有效邮箱'
    return
  }
  if (cleanUsername.length < 3) {
    error.value = '用户名至少 3 位'
    return
  }
  if (password.value.length < 8) {
    error.value = '密码至少 8 位'
    return
  }
  loading.value = true
  try {
    await auth.register(cleanEmail, cleanUsername, password.value)
    router.push('/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-[80vh] items-center justify-center">
    <form class="grid w-full max-w-sm gap-3 rounded-lg border border-slate-200 bg-white p-8" @submit.prevent="submit">
      <h1 class="text-center text-2xl font-bold tracking-tight">创建账号</h1>
      <input v-model="email" class="w-full rounded-input border border-slate-300 bg-white px-3 py-2.5" placeholder="邮箱" type="email" autocomplete="off" />
      <input v-model="username" class="w-full rounded-input border border-slate-300 bg-white px-3 py-2.5" placeholder="用户名（至少 3 位）" autocomplete="off" />
      <div class="relative">
        <input v-model="password" class="w-full rounded-input border border-slate-300 bg-white py-2.5 pl-3 pr-10" :type="showPw ? 'text' : 'password'" placeholder="密码（至少 8 位）" autocomplete="new-password" />
        <button type="button" class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600" @click="showPw = !showPw">
          <svg v-if="showPw" class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M15 12a3 3 0 01-3 3m0 0a3 3 0 01-3-3m3 3V9" /></svg>
          <svg v-else class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" /></svg>
        </button>
      </div>
      <p v-if="error" class="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{{ error }}</p>
      <AppButton :loading="loading" class="w-full justify-center py-2.5" @click="submit">注册</AppButton>
      <p class="text-center text-sm text-slate-600">
        已有账号？<RouterLink class="font-medium text-brand-600 hover:text-brand-700" to="/login">登录</RouterLink>
      </p>
    </form>
  </div>
</template>
