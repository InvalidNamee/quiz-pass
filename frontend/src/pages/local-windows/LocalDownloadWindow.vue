<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { emit } from '@tauri-apps/api/event'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { ElMessageBox } from 'element-plus'
import { DownloadCloud } from '@lucide/vue'
import { downloadBankToLocal } from '../../local/banks'
import { useToast } from '../../composables/useToast'
import type { UtilityWindowCompletedPayload } from '../../features/utility-windows/utilityWindow'

const route = useRoute()
const toast = useToast()
const downloading = ref(false)

const payload = computed<Record<string, unknown>>(() => {
  const raw = route.query.payload
  if (typeof raw !== 'string' || !raw.trim()) return {}
  try {
    return JSON.parse(decodeURIComponent(raw)) as Record<string, unknown>
  } catch {
    return {}
  }
})
const requestId = computed(() => String(payload.value.requestId || 'legacy-local-download'))
const remoteBankId = computed(() => Number(payload.value.remoteBankId || route.query.remoteBankId))
const title = computed(() => String(payload.value.title || route.query.title || '题库'))
const alreadyDownloaded = computed(() => Boolean(payload.value.alreadyDownloaded ?? route.query.alreadyDownloaded === 'true'))

async function download() {
  if (!remoteBankId.value) return
  if (alreadyDownloaded.value) {
    try {
      await ElMessageBox.confirm(
        '更新会覆盖本机保存的题库内容快照。已有本地练习记录不会被删除，但历史记录可能按新的题面展示；建议先同步作答记录。',
        '确认更新本地副本',
        { confirmButtonText: '继续更新', cancelButtonText: '取消', type: 'warning' },
      )
    } catch {
      return
    }
  }
  downloading.value = true
  try {
    const local = await downloadBankToLocal(remoteBankId.value)
    const completed: UtilityWindowCompletedPayload = {
      kind: 'local-download',
      requestId: requestId.value,
      action: 'local-bank-downloaded',
      result: {
        remoteBankId: remoteBankId.value,
        localBankId: local.id,
        downloadedAt: local.downloaded_at,
      },
    }
    await emit('utility-window-completed', completed)
    await getCurrentWindow().close()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '下载到本机失败', 'error')
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <section class="min-h-screen bg-white p-4 text-slate-700">
    <div class="space-y-4">
      <div>
        <h1 class="m-0 flex items-center gap-2 text-base font-semibold text-slate-900">
          <DownloadCloud :size="18" class="text-indigo-500" />
          {{ alreadyDownloaded ? '更新本地副本' : '下载到本机' }}
        </h1>
        <p class="mt-1 text-sm text-slate-500">{{ title }}</p>
      </div>

      <div class="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-500">
        {{ alreadyDownloaded ? '会覆盖本地题库内容快照；已有本地练习记录会保留，更新前建议先同步作答记录。' : '下载后可在弱网或断网时进入本地题库练习。' }}
      </div>

      <div class="flex justify-end gap-2 pt-2">
        <el-button @click="getCurrentWindow().close()">取消</el-button>
        <el-button type="primary" :loading="downloading" @click="download">
          {{ alreadyDownloaded ? '更新副本' : '下载' }}
        </el-button>
      </div>
    </div>
  </section>
</template>
