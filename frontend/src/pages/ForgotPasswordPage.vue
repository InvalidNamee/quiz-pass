<script setup lang="ts">
import { ref } from 'vue'
import { forgotPassword } from '../api/v2/auth'
import { useToast } from '../composables/useToast'

const email = ref('')
const loading = ref(false)
const sentMessage = ref('')
const toast = useToast()

async function submit() {
  const cleanEmail = email.value.trim()
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) { toast.show('请输入正确的邮箱地址', 'error'); return }
  loading.value = true
  try {
    const result = await forgotPassword(cleanEmail)
    sentMessage.value = result.message || '如果邮箱存在，重置链接会发送到该邮箱'
    toast.show(sentMessage.value, 'success')
  } catch (e) {
    toast.show(e instanceof Error ? e.message : '发送失败', 'error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-[80vh] items-center justify-center">
    <el-form class="w-full max-w-sm border border-slate-200 bg-white p-5" label-position="top" @submit.prevent>
      <h1 class="mb-4 text-center text-lg font-semibold text-slate-900">忘记密码</h1>
      <el-form-item label="注册邮箱">
        <el-input v-model="email" autocomplete="email" @keyup.enter="submit" />
      </el-form-item>
      <el-button type="primary" :loading="loading" class="w-full" @click="submit">发送重置邮件</el-button>
      <el-alert v-if="sentMessage" class="mt-4" type="success" :closable="false" show-icon>
        <template #title>{{ sentMessage }}</template>
      </el-alert>
      <p class="mt-4 text-center text-sm"><router-link to="/login" class="text-blue-600">返回登录</router-link></p>
    </el-form>
  </div>
</template>
