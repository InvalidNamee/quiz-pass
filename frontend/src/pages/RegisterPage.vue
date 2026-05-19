<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref(''); const username = ref(''); const password = ref(''); const loading = ref(false)
const auth = useAuthStore(); const router = useRouter()

async function submit() {
  const cleanEmail = email.value.trim(); const cleanUsername = username.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) return
  if (cleanUsername.length < 3) return
  if (password.value.length < 8) return
  loading.value = true
  try { await auth.register(cleanEmail, cleanUsername, password.value); router.push('/dashboard') }
  catch (e: any) {}
  finally { loading.value = false }
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
      <p class="mt-4 text-center text-sm text-slate-500">已有账号？<router-link to="/login" class="text-blue-600">登录</router-link></p>
    </el-form>
  </div>
</template>
