<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const identifier = ref('')
const password = ref('')
const error = ref('')
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  try {
    await auth.login(identifier.value, password.value)
    router.push('/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败'
  }
}
</script>

<template>
  <section class="mx-auto mt-[12vh] grid max-w-sm gap-3 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
    <h1 class="text-2xl font-bold">登录</h1>
    <input v-model="identifier" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="用户名或邮箱" autocomplete="username" />
    <input v-model="password" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="密码" type="password" />
    <p v-if="error" class="text-red-700">{{ error }}</p>
    <button class="rounded-md bg-blue-600 px-4 py-2 text-white" @click="submit">登录</button>
    <RouterLink class="text-blue-700" to="/register">创建账号</RouterLink>
  </section>
</template>
