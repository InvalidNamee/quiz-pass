<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ExternalLink, RefreshCw, RotateCcw, Trash2 } from '@lucide/vue'
import {
  clearLocalSyncWarning,
  deleteLocalSession,
  listLocalHistory,
  listLocalSyncWarnings,
  syncPendingLocalSessions,
  type LocalSyncWarning,
} from '../local/practice'
import type { LocalPracticeSession } from '../local/types'
import { useToast } from '../composables/useToast'
import { formatDateTime } from '../utils/dateTime'

const router = useRouter()
const toast = useToast()
const sessions = ref<LocalPracticeSession[]>([])
const warnings = ref<LocalSyncWarning[]>([])
const loading = ref(false)
const syncing = ref(false)

async function load() {
  loading.value = true
  try {
    const [history, syncWarnings] = await Promise.all([listLocalHistory(), listLocalSyncWarnings()])
    sessions.value = history
    warnings.value = syncWarnings
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
    const outdatedText = result.outdated_banks.length ? `，${result.outdated_banks.length} 个题库需要更新副本` : ''
    const failedText = result.failed.length ? `，${result.failed.length} 条失败` : ''
    toast.show(
      `同步完成，上传 ${result.synced.length} 条、下载 ${result.downloaded} 条${failedText}${outdatedText}`,
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

function syncStatusLabel(status: string) {
  return ({ synced: '已同步', failed: '同步失败', pending: '待同步', syncing: '同步中' } as Record<string, string>)[status] || status
}

function syncStatusType(status: string) {
  if (status === 'synced') return 'success'
  if (status === 'failed') return 'danger'
  return 'warning'
}

function modeLabel(mode: string) {
  return ({ practice: '练习', exam: '模拟考试', mistake_review: '错题练习' } as Record<string, string>)[mode] || mode
}

function statusLabel(status: string) {
  return ({ in_progress: '进行中', submitted: '已提交' } as Record<string, string>)[status] || status
}

function retrySync(row: LocalPracticeSession) {
  if (row.sync_status === 'synced') return
  syncNow()
}

async function removeSession(row: LocalPracticeSession) {
  try {
    await ElMessageBox.confirm(
      row.sync_status === 'synced'
        ? '删除后只会清理本机记录，服务器上的同步记录不受影响。'
        : '这条记录尚未成功同步，删除后将无法再上传到服务器。确定删除吗？',
      '删除本地记录',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
    await deleteLocalSession(row.id)
    toast.show('本地记录已删除', 'success')
    await load()
  } catch {
    // 用户取消
  }
}

async function dismissWarning(warning: LocalSyncWarning) {
  await clearLocalSyncWarning(warning.key)
  warnings.value = warnings.value.filter((item) => item.key !== warning.key)
}

function updateLocalBank(warning: LocalSyncWarning) {
  router.push(`/banks/${warning.remote_bank_id}`)
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

    <div v-if="warnings.length" class="space-y-2">
      <el-alert
        v-for="warning in warnings"
        :key="warning.key"
        type="warning"
        show-icon
        :closable="false"
        class="qp-section !py-3"
      >
        <template #title>{{ warning.message }}</template>
        <div class="mt-1 flex flex-wrap items-center gap-2 text-sm">
          <span class="text-slate-600">
            远端练习记录暂未拉到本机。缺失题目 ID：
            {{ warning.missing_question_ids.slice(0, 8).join(', ') }}{{ warning.missing_question_ids.length > 8 ? '…' : '' }}
          </span>
          <el-button size="small" class="qp-icon-button is-blue" @click="updateLocalBank(warning)">
            <RefreshCw :size="15" />更新副本
          </el-button>
          <el-button size="small" class="qp-icon-button" @click="dismissWarning(warning)">忽略</el-button>
        </div>
      </el-alert>
    </div>

    <el-table v-loading="loading" :data="sessions" border size="small" @row-click="openSession">
      <el-table-column prop="id" label="本地 ID" width="90" />
      <el-table-column label="模式" width="110">
        <template #default="{ row }">{{ modeLabel(row.mode) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">{{ statusLabel(row.status) }}</template>
      </el-table-column>
      <el-table-column label="进度/得分" min-width="180">
        <template #default="{ row }">
          <span v-if="row.status === 'submitted'">{{ row.score }} 分 · {{ row.correct_count }}/{{ row.total_questions }}</span>
          <span v-else>进行中 · {{ row.total_questions }} 题</span>
        </template>
      </el-table-column>
      <el-table-column label="同步" min-width="210">
        <template #default="{ row }">
          <div class="flex min-w-0 flex-col gap-1">
            <el-tag :type="syncStatusType(row.sync_status)">{{ syncStatusLabel(row.sync_status) }}</el-tag>
            <span v-if="row.sync_error" class="line-clamp-2 text-xs text-rose-500">{{ row.sync_error }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" min-width="180">
        <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" align="left" header-align="left">
        <template #default="{ row }">
          <div class="flex items-center gap-1" @click.stop>
            <el-button size="small" class="qp-icon-button is-blue" @click="openSession(row)">
              <ExternalLink :size="15" />
            </el-button>
            <el-button
              size="small"
              :disabled="row.sync_status === 'synced'"
              class="qp-icon-button is-amber"
              @click="retrySync(row)"
            >
              <RotateCcw :size="15" />
            </el-button>
            <el-button size="small" class="qp-icon-button is-red" @click="removeSession(row)">
              <Trash2 :size="15" />
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </section>
</template>
