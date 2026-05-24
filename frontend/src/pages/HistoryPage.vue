<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listHistory } from '../api/v2/practice'
import type { Page, PracticeSession } from '../api/types'
import { practiceProgressColor, practiceProgressPercent, practiceProgressText, practiceProgressType } from '../utils/practiceProgress'
import { formatDateTime } from '../utils/dateTime'

const route = useRoute(); const router = useRouter()
const sessions = ref<PracticeSession[]>([])
const mode = ref(''); const status = ref('')
const pageInfo = ref<Page<PracticeSession> | null>(null)
const loading = ref(true)

type TagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

function modeBadge(m: string): TagType {
  const map: Record<string, TagType> = { practice: 'info', exam: 'warning', mistake_review: 'danger' }
  return map[m]
}
function modeText(m: string) { const map: Record<string, string> = { practice: '练习', exam: '考试', mistake_review: '错题' }; return map[m] || m }
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
      <div>
        <h1 class="qp-title">练习记录</h1>
        <p class="qp-subtitle">查看历史练习、继续未完成会话，或进入已提交结果页。</p>
      </div>
    </div>

    <div class="qp-toolbar rounded-2xl border border-slate-100 bg-white p-3 shadow-sm">
      <el-select v-model="mode" size="small" placeholder="模式" clearable class="!w-32" @change="applyFilters()">
        <el-option label="普通练习" value="practice" /><el-option label="模拟考试" value="exam" /><el-option label="错题复习" value="mistake_review" />
      </el-select>
      <el-select v-model="status" size="small" placeholder="状态" clearable class="!w-32" @change="applyFilters()">
        <el-option label="进行中" value="in_progress" /><el-option label="已提交" value="submitted" />
      </el-select>
    </div>

    <el-table
      v-loading="loading"
      :data="sessions"
      stripe
      size="small"
      highlight-current-row
      class="cursor-pointer border border-slate-100 !rounded-2xl shadow-sm"
      @row-click="(row: PracticeSession) => router.push(row.status === 'in_progress' ? `/practice/session/${row.id}` : `/practice/result/${row.id}`)"
    >
      <el-table-column label="题库" min-width="160">
        <template #default="{ row }: { row: PracticeSession }">{{ row.bank_title || `题库 #${row.bank_id}` }}</template>
      </el-table-column>
      <el-table-column label="模式" width="80">
        <template #default="{ row }: { row: PracticeSession }"><el-tag size="small" :type="modeBadge(row.mode)">{{ modeText(row.mode) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="状态" width="80">
        <template #default="{ row }: { row: PracticeSession }"><el-tag size="small" :type="row.status === 'submitted' ? 'success' : 'warning'">{{ row.status === 'submitted' ? '已提交' : '进行中' }}</el-tag></template>
      </el-table-column>
      <el-table-column label="进度" width="210">
        <template #default="{ row }: { row: PracticeSession }">
          <div class="grid gap-1">
            <div class="flex items-center justify-between gap-2 text-xs">
              <span class="font-semibold text-slate-500">{{ practiceProgressType(row) }}</span>
              <span class="text-slate-400">{{ practiceProgressText(row) }}</span>
            </div>
            <el-progress
              :percentage="practiceProgressPercent(row)"
              :color="practiceProgressColor(row)"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="190">
        <template #default="{ row }: { row: PracticeSession }">{{ formatDateTime(row.started_at, '无') }}</template>
      </el-table-column>
      <el-table-column label="最后作答" width="190">
        <template #default="{ row }: { row: PracticeSession }">{{ formatDateTime(lastActivity(row), '无') }}</template>
      </el-table-column>
    </el-table>

    <el-pagination v-if="pageInfo && pageInfo.total_pages > 1" v-model:current-page="pageInfo.page" :total="pageInfo.total" :page-size="pageInfo.page_size" layout="prev, pager, next, total" size="small" background @current-change="goPage" />
  </div>
</template>
