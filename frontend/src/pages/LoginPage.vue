<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const identifier = ref(''); const password = ref(''); const loading = ref(false)
const auth = useAuthStore(); const router = useRouter()

async function submit() {
  loading.value = true
  try { await auth.login(identifier.value, password.value); router.push('/dashboard') }
  catch (e: any) { /* error shown by store */ }
  finally { loading.value = false }
}
</script>

<template>
  <div class="flex min-h-[80vh] items-center justify-center">
    <el-form class="w-full max-w-sm border border-slate-200 bg-white p-5" label-position="top" @submit.prevent>
      <h1 class="mb-4 text-center text-lg font-semibold text-slate-900">Quiz Pass</h1>
      <el-form-item label="用户名或邮箱"><el-input v-model="identifier" autocomplete="username" @keyup.enter="submit" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="password" type="password" autocomplete="current-password" show-password @keyup.enter="submit" /></el-form-item>
      <el-button type="primary" :loading="loading" class="w-full" @click="submit">登录</el-button>
      <p class="mt-4 text-center text-sm text-slate-500">还没有账号？<router-link to="/register" class="text-blue-600">注册</router-link></p>
    </el-form>
  </div>
</template>
