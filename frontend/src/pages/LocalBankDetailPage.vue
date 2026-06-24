<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { Play, RefreshCw } from '@lucide/vue'
import { getLocalBank, getLocalQuestions } from '../local/banks'
import { syncPendingLocalSessions } from '../local/practice'
import type { LocalBank, LocalQuestion } from '../local/types'
import { useToast } from '../composables/useToast'
import { formatDateTime } from '../utils/dateTime'
import { openLocalPracticeSetupWindow } from '../features/local/openLocalWindow'

const route = useRoute()
const toast = useToast()
const bank = ref<LocalBank | null>(null)
const questions = ref<LocalQuestion[]>([])
const loading = ref(false)
const syncing = ref(false)

async function load() {
  loading.value = true
  try {
    const id = Number(route.params.localBankId)
    bank.value = await getLocalBank(id)
    if (!bank.value) throw new Error('本地题库不存在')
    questions.value = await getLocalQuestions(id)
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载本地题库失败', 'error')
  } finally {
    loading.value = false
  }
}

function openPracticeSetup() {
  if (!bank.value) return
  openLocalPracticeSetupWindow({ localBankId: bank.value.id, title: bank.value.title }).catch((error) => {
    toast.show(error instanceof Error ? error.message : '打开本地练习窗口失败', 'error')
  })
}

async function syncNow() {
  syncing.value = true
  try {
    const result = await syncPendingLocalSessions()
    toast.show(
      result.failed.length ? `同步完成，上传 ${result.synced.length} 条、下载 ${result.downloaded} 条，${result.failed.length} 条失败` : `同步完成，上传 ${result.synced.length} 条、下载 ${result.downloaded} 条`,
      result.failed.length ? 'info' : 'success',
    )
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '同步失败', 'error')
  } finally {
    syncing.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading" class="qp-page space-y-4">
    <div v-if="bank" class="qp-section">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 class="qp-page-title">{{ bank.title }}</h1>
          <p class="qp-page-subtitle">{{ bank.description || '本地只读题库副本' }}</p>
          <div class="mt-2 flex flex-wrap items-center gap-1.5">
            <el-tag v-for="tag in bank.tags" :key="tag.id" size="small" type="info">{{ tag.name }}</el-tag>
            <el-tag size="small">本地副本</el-tag>
            <span class="text-xs text-slate-400">下载于 {{ formatDateTime(bank.downloaded_at) }}</span>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <el-button type="primary" @click="openPracticeSetup"><Play :size="14" class="mr-1" />开始练习</el-button>
          <el-button :loading="syncing" @click="syncNow"><RefreshCw :size="14" class="mr-1" />同步记录</el-button>
        </div>
      </div>
      <el-descriptions :column="3" border class="mt-4" size="small">
        <el-descriptions-item label="题目数量">{{ questions.length }} 题</el-descriptions-item>
        <el-descriptions-item label="远端题库">#{{ bank.remote_bank_id }}</el-descriptions-item>
        <el-descriptions-item label="远端更新时间">{{ formatDateTime(bank.remote_updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="qp-section">
      <div class="mb-3 flex items-center justify-between">
        <h2 class="qp-section-title !mb-0">本地题目预览</h2>
        <el-button text :loading="loading" @click="load"><RefreshCw :size="14" class="mr-1" />刷新</el-button>
      </div>
      <el-table :data="questions" size="small" border>
        <el-table-column type="index" width="56" label="#" />
        <el-table-column prop="type" label="题型" width="110" />
        <el-table-column prop="stem" label="题干" min-width="320" show-overflow-tooltip />
      </el-table>
    </div>
  </section>
</template>
