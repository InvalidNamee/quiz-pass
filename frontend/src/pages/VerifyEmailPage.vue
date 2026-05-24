<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { verifyEmail } from '../api/v2/auth'

const route = useRoute()
const loading = ref(true)
const status = ref<'success' | 'error'>('success')
const message = ref('正在验证邮箱...')

onMounted(async () => {
  const token = String(route.query.token || '')
  if (!token) {
    status.value = 'error'
    message.value = '验证链接缺少 token'
    loading.value = false
    return
  }
  try {
    const result = await verifyEmail(token)
    status.value = 'success'
    message.value = result.message || '邮箱验证成功，现在可以登录'
  } catch (e) {
    status.value = 'error'
    message.value = e instanceof Error ? e.message : '邮箱验证失败'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="flex min-h-[80vh] items-center justify-center">
    <div class="w-full max-w-sm border border-slate-200 bg-white p-4">
      <h1 class="mb-4 text-center text-lg font-semibold text-slate-900">邮箱验证</h1>
      <el-skeleton v-if="loading" :rows="3" animated />
      <template v-else>
        <el-alert :type="status" :title="message" :closable="false" show-icon />
        <router-link to="/login">
          <el-button class="mt-4 w-full" type="primary">去登录</el-button>
        </router-link>
      </template>
    </div>
  </div>
</template>
