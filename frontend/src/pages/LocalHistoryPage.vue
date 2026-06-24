<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { RefreshCw } from '@lucide/vue'
import { listLocalHistory, syncPendingLocalSessions } from '../local/practice'
import type { LocalPracticeSession } from '../local/types'
import { useToast } from '../composables/useToast'
import { formatDateTime } from '../utils/dateTime'

const router = useRouter()
const toast = useToast()
const sessions = ref<LocalPracticeSession[]>([])
const loading = ref(false)
const syncing = ref(false)

async function load() {
  loading.value = true
  try {
    sessions.value = await listLocalHistory()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载本地记录失败', 'error')
  } finally {
    loading.value = false
  }
}

async function syncNow() {
  syncing.value = true
  try {
    const result = await syncPendingLocalSessions()
    toast.show(
      result.failed.length ? `同步完成，上传 ${result.synced.length} 条、下载 ${result.downloaded} 条，${result.failed.length} 条失败` : `同步完成，上传 ${result.synced.length} 条、下载 ${result.downloaded} 条`,
      result.failed.length ? 'info' : 'success',
    )
    await load()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '同步失败', 'error')
  } finally {
    syncing.value = false
  }
}

function openSession(row: LocalPracticeSession) {
  router.push(row.status === 'submitted' ? `/local/practice/result/${row.id}` : `/local/practice/session/${row.id}`)
}

onMounted(load)
</script>

<template>
  <section class="qp-page space-y-4">
    <div class="qp-section flex items-center justify-between gap-3">
      <div>
        <h1 class="qp-page-title">本地练习记录</h1>
        <p class="qp-page-subtitle">本机保存的练习和考试记录，联网后可同步到服务器。</p>
      </div>
      <div class="flex gap-2">
        <el-button :loading="loading" @click="load"><RefreshCw :size="14" class="mr-1" />刷新</el-button>
        <el-button type="primary" :loading="syncing" @click="syncNow"><RefreshCw :size="14" class="mr-1" />立即同步</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="sessions" border size="small" @row-click="openSession">
      <el-table-column prop="id" label="本地 ID" width="90" />
      <el-table-column prop="mode" label="模式" width="110" />
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column label="进度/得分" min-width="180">
        <template #default="{ row }">
          <span v-if="row.status === 'submitted'">{{ row.score }} 分 · {{ row.correct_count }}/{{ row.total_questions }}</span>
          <span v-else>进行中 · {{ row.total_questions }} 题</span>
        </template>
      </el-table-column>
      <el-table-column label="同步" width="140">
        <template #default="{ row }">
          <el-tag :type="row.sync_status === 'synced' ? 'success' : row.sync_status === 'failed' ? 'danger' : 'warning'">{{ row.sync_status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
      </el-table-column>
    </el-table>
  </section>
</template>
