<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listHistory } from '../api/practice'
import type { Page, PracticeSession } from '../api/types'

const route = useRoute(); const router = useRouter()
const sessions = ref<PracticeSession[]>([])
const mode = ref(''); const status = ref('')
const pageInfo = ref<Page<PracticeSession> | null>(null)
const loading = ref(true)

function modeBadge(m: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = { practice: '', exam: 'warning', mistake_review: 'danger' }
  return map[m] || ''
}
function modeText(m: string) { const map: Record<string, string> = { practice: '练习', exam: '考试', mistake_review: '错题' }; return map[m] || m }
function formatTime(value: string | null | undefined) {
  if (!value) return '无'
  return new Date(value).toLocaleString()
}
function lastActivity(row: PracticeSession) {
  return row.last_answered_at || row.submitted_at || row.started_at
}

async function load() {
  mode.value = String(route.query.mode || ''); status.value = String(route.query.status || '')
  loading.value = true
  try { const data = await listHistory({ page: Number(route.query.page || 1), mode: mode.value || undefined, status: status.value || undefined }); pageInfo.value = data; sessions.value = data.items } finally { loading.value = false }
}
function applyFilters(page = 1) { const q: Record<string, string> = {}; if (page > 1) q.page = String(page); if (mode.value) q.mode = mode.value; if (status.value) q.status = status.value; router.push({ query: q }) }
function goPage(p: number) { applyFilters(p) }

onMounted(load); watch(() => route.fullPath, load)
</script>

<template>
  <div class="qp-page">
    <div class="qp-titlebar">
      <h1 class="qp-title">刷题记录</h1>
      <div class="flex flex-wrap gap-2">
        <el-select v-model="mode" size="small" placeholder="模式" clearable class="!w-28" @change="applyFilters()">
          <el-option label="普通练习" value="practice" /><el-option label="模拟考试" value="exam" /><el-option label="错题复习" value="mistake_review" />
        </el-select>
        <el-select v-model="status" size="small" placeholder="状态" clearable class="!w-28" @change="applyFilters()">
          <el-option label="进行中" value="in_progress" /><el-option label="已提交" value="submitted" />
        </el-select>
      </div>
    </div>

    <el-table v-loading="loading" :data="sessions" stripe size="small" highlight-current-row @row-click="(row: PracticeSession) => router.push(row.status === 'in_progress' ? `/practice/session/${row.id}` : `/practice/result/${row.id}`)" class="cursor-pointer">
      <el-table-column label="题库" min-width="160">
        <template #default="{ row }: { row: PracticeSession }">{{ row.bank_title || `题库 #${row.bank_id}` }}</template>
      </el-table-column>
      <el-table-column label="模式" width="80">
        <template #default="{ row }: { row: PracticeSession }"><el-tag size="small" :type="modeBadge(row.mode)">{{ modeText(row.mode) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }: { row: PracticeSession }"><el-tag size="small" :type="row.status === 'submitted' ? 'success' : 'warning'">{{ row.status === 'submitted' ? '已提交' : '进行中' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="进度" width="100" align="right">
        <template #default="{ row }: { row: PracticeSession }">
          <span v-if="row.status === 'in_progress'">{{ row.answered_count }}/{{ row.total_questions }}</span>
          <span v-else :class="{ 'text-green-600': (row.score||0) >= 80, 'text-orange-600': (row.score||0) >= 60 && (row.score||0) < 80, 'text-red-600': (row.score||0) < 60 }">{{ row.score }}分</span>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="190">
        <template #default="{ row }: { row: PracticeSession }">{{ formatTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="最后进入" width="190">
        <template #default="{ row }: { row: PracticeSession }">{{ formatTime(lastActivity(row)) }}</template>
      </el-table-column>
    </el-table>

    <el-pagination v-if="pageInfo && pageInfo.total_pages > 1" v-model:current-page="pageInfo.page" :total="pageInfo.total" :page-size="pageInfo.page_size" layout="prev, pager, next, total" size="small" background @current-change="goPage" />
  </div>
</template>
