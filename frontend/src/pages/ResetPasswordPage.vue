<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { resetPassword } from '../api/v2/auth'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const token = computed(() => String(route.query.token || ''))
const password = ref('')
const loading = ref(false)
const toast = useToast()

async function submit() {
  if (!token.value) { toast.show('重置链接缺少 token', 'error'); return }
  if (password.value.length < 8) { toast.show('新密码至少 8 位', 'error'); return }
  loading.value = true
  try {
    const result = await resetPassword(token.value, password.value)
    toast.show(result.message || '密码已重置，请重新登录', 'success')
    router.push('/login')
  } catch (e) {
    toast.show(e instanceof Error ? e.message : '重置失败', 'error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-[80vh] items-center justify-center">
    <el-form class="w-full max-w-sm border border-slate-200 bg-white p-5" label-position="top" @submit.prevent>
      <h1 class="mb-4 text-center text-lg font-semibold text-slate-900">重置密码</h1>
      <el-alert v-if="!token" class="mb-4" type="error" title="重置链接缺少 token" :closable="false" show-icon />
      <el-form-item label="新密码">
        <el-input v-model="password" type="password" autocomplete="new-password" placeholder="至少 8 位" show-password @keyup.enter="submit" />
      </el-form-item>
      <el-button type="primary" :disabled="!token" :loading="loading" class="w-full" @click="submit">重置密码</el-button>
      <p class="mt-4 text-center text-sm"><router-link to="/login" class="text-blue-600">返回登录</router-link></p>
    </el-form>
  </div>
</template>
