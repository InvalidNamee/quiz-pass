<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { emit } from '@tauri-apps/api/event'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { ClipboardList, HardDrive, Play } from '@lucide/vue'
import { getLocalBank } from '../../local/banks'
import { createLocalSession } from '../../local/practice'
import type { LocalBank } from '../../local/types'
import { useToast } from '../../composables/useToast'
import type { UtilityWindowCompletedPayload } from '../../features/utility-windows/utilityWindow'

const route = useRoute()
const toast = useToast()
const bank = ref<LocalBank | null>(null)
const loading = ref(false)
const starting = ref(false)
const mode = ref<'practice' | 'exam'>('practice')

const payload = computed<Record<string, unknown>>(() => {
  const raw = route.query.payload
  if (typeof raw !== 'string' || !raw.trim()) return {}
  try {
    return JSON.parse(decodeURIComponent(raw)) as Record<string, unknown>
  } catch {
    return {}
  }
})
const requestId = computed(() => String(payload.value.requestId || 'legacy-local-practice-setup'))
const localBankId = computed(() => Number(payload.value.localBankId || route.query.localBankId))
const title = computed(() => bank.value?.title || String(payload.value.title || route.query.title || '本地题库'))

async function load() {
  if (!localBankId.value) return
  loading.value = true
  try {
    bank.value = await getLocalBank(localBankId.value)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载本地题库失败', 'error')
  } finally {
    loading.value = false
  }
}

async function start() {
  if (!localBankId.value) return
  starting.value = true
  try {
    const sessionId = await createLocalSession(localBankId.value, mode.value)
    const completed: UtilityWindowCompletedPayload = {
      kind: 'local-practice-setup',
      requestId: requestId.value,
      action: 'practice-created',
      result: { localSessionId: sessionId, localBankId: localBankId.value },
    }
    await emit('utility-window-completed', completed)
    await getCurrentWindow().close()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '创建本地练习失败', 'error')
  } finally {
    starting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading" class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 flex items-center gap-2 text-base font-semibold text-slate-900">
          <HardDrive :size="18" class="text-indigo-500" />开始本地练习
        </h1>
        <p class="mt-1 text-sm text-slate-500">{{ title }}</p>
      </div>

      <div class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-500">
        本地练习会直接写入本机 SQLite，联网后可在本地记录中同步到服务器。
      </div>

      <el-radio-group v-model="mode" class="w-full">
        <el-radio-button label="practice">
          <span class="inline-flex items-center gap-1"><Play :size="14" />练习模式</span>
        </el-radio-button>
        <el-radio-button label="exam">
          <span class="inline-flex items-center gap-1"><ClipboardList :size="14" />模拟考试</span>
        </el-radio-button>
      </el-radio-group>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="getCurrentWindow().close()">取消</el-button>
        <el-button type="primary" :loading="starting" @click="start">开始</el-button>
      </div>
    </div>
  </section>
</template>
