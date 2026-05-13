<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const username = ref('')
const password = ref('')
const error = ref('')
const auth = useAuthStore()
const router = useRouter()

async function submit() {
  error.value = ''
  try {
    await auth.register(email.value, username.value, password.value)
    router.push('/dashboard')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '注册失败'
  }
}
</script>

<template>
  <section class="mx-auto mt-[12vh] grid max-w-sm gap-3 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
    <h1 class="text-2xl font-bold">注册</h1>
    <input v-model="email" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="邮箱" />
    <input v-model="username" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="用户名" />
    <input v-model="password" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="密码" type="password" />
    <p v-if="error" class="text-red-700">{{ error }}</p>
    <button class="rounded-md bg-blue-600 px-4 py-2 text-white" @click="submit">注册</button>
    <RouterLink class="text-blue-700" to="/login">已有账号</RouterLink>
  </section>
</template>
