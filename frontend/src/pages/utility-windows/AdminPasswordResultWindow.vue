<script setup lang="ts">
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  userId?: number
  temporaryPassword?: string
  requestId?: string
}

const { payload, closeWindow } = useUtilityWindowPage<Payload>('admin-password-result')
</script>

<template>
  <section class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">临时密码</h1>
        <p class="mt-1 text-sm text-slate-500">临时密码仅显示一次，请立即交给用户。</p>
      </div>
      <code class="block rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-base font-semibold text-slate-900">
        {{ payload.temporaryPassword }}
      </code>
      <div class="flex justify-end pt-2">
        <el-button type="primary" @click="closeWindow">我已记录</el-button>
      </div>
    </div>
  </section>
</template>
