<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { RefreshCw, HardDrive, Wifi } from '@lucide/vue'
import { listLocalBanks } from '../local/banks'
import { syncPendingLocalSessions } from '../local/practice'
import type { LocalBank } from '../local/types'
import { useToast } from '../composables/useToast'
import { formatDateTime } from '../utils/dateTime'

const toast = useToast()
const banks = ref<LocalBank[]>([])
const loading = ref(false)
const syncing = ref(false)

async function load() {
  loading.value = true
  try {
    banks.value = await listLocalBanks()
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '加载本地题库失败', 'error')
  } finally {
    loading.value = false
  }
}

async function syncNow() {
  syncing.value = true
  try {
    const result = await syncPendingLocalSessions()
    const failed = result.failed.length
    toast.show(failed ? `同步完成，${failed} 条记录失败` : `同步完成，${result.synced.length} 条记录已上传`, failed ? 'info' : 'success')
  } catch (error) {
    toast.show(error instanceof Error ? error.message : '同步失败，稍后可重试', 'error')
  } finally {
    syncing.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="qp-page space-y-4">
    <div class="qp-section flex items-center justify-between gap-3">
      <div>
        <h1 class="qp-page-title flex items-center gap-2"><HardDrive :size="20" />本地题库</h1>
        <p class="qp-page-subtitle">下载到本机的只读题库，可在弱网或断网时继续练习。</p>
      </div>
      <div class="flex gap-2">
        <el-button :loading="loading" @click="load"><RefreshCw :size="14" class="mr-1" />刷新</el-button>
        <el-button type="primary" :loading="syncing" @click="syncNow"><Wifi :size="14" class="mr-1" />立即同步</el-button>
      </div>
    </div>

    <div v-loading="loading" class="grid gap-2">
      <RouterLink
        v-for="bank in banks"
        :key="bank.id"
        :to="`/local/banks/${bank.id}`"
        class="rounded-lg border border-slate-200 bg-white px-4 py-3 transition-colors hover:border-indigo-200 hover:bg-indigo-50/30"
      >
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="min-w-0">
            <h2 class="truncate text-base font-semibold text-slate-800">{{ bank.title }}</h2>
            <p class="mt-1 line-clamp-1 text-sm text-slate-500">{{ bank.description || '暂无描述' }}</p>
          </div>
          <span class="text-xs text-slate-400">下载于 {{ formatDateTime(bank.downloaded_at) }}</span>
        </div>
        <div class="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
          <el-tag v-for="tag in bank.tags" :key="tag.id" size="small" type="info">{{ tag.name }}</el-tag>
          <span>{{ bank.question_count }} 题</span>
          <span>远端 #{{ bank.remote_bank_id }}</span>
        </div>
      </RouterLink>
      <el-empty v-if="!loading && !banks.length" description="还没有本地题库，请先在服务器题库详情中下载到本机。" />
    </div>
  </section>
</template>
