<script setup lang="ts">
import { ref } from 'vue'
import { useUtilityWindowPage } from '../../features/utility-windows/useUtilityWindowPage'

type Payload = {
  local?: boolean
  sessionId?: number
  requestId?: string
}

const { payload, complete, closeWindow } = useUtilityWindowPage<Payload>('submit-practice')
const commitCachedAnswers = ref(true)

function submitChoice() {
  complete('submit-choice', {
    commitDrafts: commitCachedAnswers.value,
    local: Boolean(payload.value.local),
    sessionId: payload.value.sessionId,
  })
}
</script>

<template>
  <section class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 text-base font-semibold text-slate-900">{{ payload.local ? '提交本地练习' : '提交试卷' }}</h1>
        <p class="mt-1 text-sm text-slate-500">
          {{ payload.local ? '提交后会在本机结算，联网后可同步到服务器。' : '提交后将结算本次练习。' }}
        </p>
      </div>

      <el-radio-group v-model="commitCachedAnswers" class="grid gap-2">
        <el-radio :value="true" border>提交当前已缓存答案并计分</el-radio>
        <el-radio :value="false" border>不提交未锁定缓存，按未作答处理</el-radio>
      </el-radio-group>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="closeWindow">继续作答</el-button>
        <el-button type="primary" @click="submitChoice">{{ payload.local ? '提交' : '提交试卷' }}</el-button>
      </div>
    </div>
  </section>
</template>
