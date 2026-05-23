<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBankList } from '../composables/useBankList'
import { favoriteBank, unfavoriteBank } from '../api/v2/banks'
import type { QuestionBankV2 } from '../api/types'
import GenerateBankDialog from './GenerateBankDialog.vue'
import PracticeSetupDialog from './PracticeSetupDialog.vue'
import TagFilterDialog from './TagFilterDialog.vue'
import AuthorFilterDialog from './AuthorFilterDialog.vue'
import { isUnstableBankStatus, isUnstableWorkflowStatus } from '../utils/generationStatus'

const props = defineProps<{
  title: string; subtitle: string
  scope: 'mine' | 'public' | 'favorites'
  showAuthorFilter?: boolean; showVisibilityFilter?: boolean; showGenerationFilter?: boolean
  allowCreate?: boolean
}>()

const route = useRoute()
const router = useRouter()
const { banks, pageInfo, keyword, selectedAuthor, selectedTags, visibility, generationStatus, loading, hasActiveFilters, load, clearAll, goPage } = useBankList(props.scope)

const createDialogVisible = ref(false)
const practiceDialogVisible = ref(false)
const selectedPracticeBank = ref<QuestionBankV2 | null>(null)
let pollingTimer: number | null = null

function hasUnstableBanks() {
  return banks.value.some((bank) =>
    isUnstableBankStatus(bank.generation_status) || isUnstableWorkflowStatus(bank.active_workflow?.status),
  )
}

function stopPolling() {
  if (pollingTimer !== null) {
    window.clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function syncPolling() {
  if (!hasUnstableBanks()) {
    stopPolling()
    return
  }
  if (pollingTimer === null) {
    pollingTimer = window.setInterval(() => {
      if (hasUnstableBanks()) void load(true)
      else stopPolling()
    }, 3000)
  }
}

async function toggleFavorite(bank: QuestionBankV2) {
  const next = !bank.is_favorited
  bank.is_favorited = next
  try { if (next) await favoriteBank(bank.id); else await unfavoriteBank(bank.id) } catch { bank.is_favorited = !next }
}

function applySearch() {
  const q: Record<string, string> = {}
  if (keyword.value.trim()) q.keyword = keyword.value.trim()
  if (props.showAuthorFilter && selectedAuthor.value?.id) q.owner_id = String(selectedAuthor.value.id)
  const tids = selectedTags.value.map(t => t.id).filter(Boolean).join(',')
  if (tids) q.tag_ids = tids
  if (visibility.value) q.visibility = visibility.value
  if (generationStatus.value) q.generation_status = generationStatus.value
  router.push({ query: q })
}

function openPractice(bank: QuestionBankV2) {
  selectedPracticeBank.value = bank
  practiceDialogVisible.value = true
}

function continuePractice(bank: QuestionBankV2) {
  if (!bank.resumable_session) return
  router.push(`/practice/session/${bank.resumable_session.id}`)
}

onMounted(load)
watch(() => route.fullPath, () => { void load() })
watch(banks, syncPolling, { deep: true })
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="qp-page">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title">{{ title }}</h1>
        <p class="qp-subtitle">{{ subtitle }}</p>
      </div>
      <div class="flex gap-2">
        <el-button v-if="allowCreate" size="small" type="primary" @click="createDialogVisible = true">新建题库</el-button>
      </div>
    </div>

    <!-- Inline filters -->
    <div class="qp-toolbar">
      <el-input v-model="keyword" size="small" placeholder="搜索…" clearable class="!w-40" @change="applySearch" />
      <AuthorFilterDialog v-if="showAuthorFilter" v-model="selectedAuthor" @update:model-value="applySearch" />
      <TagFilterDialog v-model="selectedTags" @update:model-value="applySearch" />
      <el-select v-if="showVisibilityFilter" v-model="visibility" size="small" placeholder="可见性" clearable class="!w-24" @change="applySearch">
        <el-option label="私有" value="private" />
        <el-option label="公开" value="public" />
      </el-select>
      <el-select v-if="showGenerationFilter" v-model="generationStatus" size="small" placeholder="状态" clearable class="!w-24" @change="applySearch">
        <el-option label="手动创建" value="none" />
        <el-option label="生成中" value="processing" />
        <el-option label="成功" value="succeeded" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-button v-if="hasActiveFilters" size="small" text @click="clearAll">清除</el-button>
    </div>
    <div v-if="selectedTags.length || (showAuthorFilter && selectedAuthor)" class="flex flex-wrap items-center gap-2 border-b border-slate-100 pb-2">
      <template v-if="showAuthorFilter && selectedAuthor">
        <span class="text-sm text-slate-500">已选作者</span>
        <el-tag closable size="small" type="primary" effect="plain" @close="selectedAuthor = null; applySearch()">
          <div class="flex items-center gap-1.5">
            <span>{{ selectedAuthor.display_name || selectedAuthor.username }}</span>
          </div>
        </el-tag>
      </template>
      <template v-if="selectedTags.length">
        <span v-if="!(showAuthorFilter && selectedAuthor)" class="text-sm text-slate-500">已选标签</span>
        <el-tag v-for="tag in selectedTags" :key="tag.id" closable size="small" type="primary" effect="plain" @close="selectedTags = selectedTags.filter(t => t.id !== tag.id); applySearch()">
          {{ tag.name }}
        </el-tag>
      </template>
    </div>

    <el-table v-loading="loading" :data="banks" stripe size="small" highlight-current-row @row-click="(row: QuestionBankV2) => router.push(`/banks/${row.id}`)" class="cursor-pointer">
      <el-table-column label="题库" min-width="200">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-1.5">
              <span class="font-medium">{{ row.title }}</span>
              <el-tag size="small" :type="row.visibility === 'public' ? 'success' : 'info'">{{ row.visibility === 'public' ? '公开' : '私有' }}</el-tag>
            </div>
            <span v-if="row.description" class="text-xs text-slate-400 truncate max-w-xs">{{ row.description }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="标签" width="180">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <div class="flex flex-wrap gap-1">
            <el-tag v-for="tag in row.tags.slice(0, 3)" :key="tag.id" size="small" type="info">{{ tag.name }}</el-tag>
            <span v-if="row.tags.length > 3" class="text-xs text-slate-400">+{{ row.tags.length - 3 }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="作者" width="120">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <RouterLink class="text-blue-700 hover:underline" :to="`/users/${row.owner.id}`" @click.stop>{{ row.owner.display_name || row.owner.username }}</RouterLink>
        </template>
      </el-table-column>
      <el-table-column label="题目数" width="50" align="center">
        <template #default="{ row }: { row: QuestionBankV2 }">{{ row.stats.question_count }}</template>
      </el-table-column>
      <el-table-column label="收藏数" width="50" align="center">
        <template #default="{ row }: { row: QuestionBankV2 }">{{ row.stats.favorite_count }}</template>
      </el-table-column>
      <el-table-column width="64" align="center">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <el-button
            size="small"
            text
            :class="['favorite-button', row.is_favorited ? 'is-favorited' : '']"
            @click.stop="toggleFavorite(row)"
          >{{ row.is_favorited ? '★' : '☆' }}</el-button>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" align="right">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <div class="flex items-center justify-end gap-1">
            <el-button v-if="row.resumable_session" size="small" type="primary" plain @click.stop="continuePractice(row)">继续</el-button>
            <el-button v-if="row.permissions.can_practice" size="small" @click.stop="openPractice(row)">练习</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="pageInfo && pageInfo.total_pages > 1"
      v-model:current-page="pageInfo.page"
      :total="pageInfo.total"
      :page-size="pageInfo.page_size"
      layout="prev, pager, next, total"
      size="small"
      background
      @current-change="goPage"
    />


    <GenerateBankDialog v-model="createDialogVisible" @submitted="load" />
    <PracticeSetupDialog
      v-model="practiceDialogVisible"
      :bank-id="selectedPracticeBank?.id ?? null"
      :initial-bank="selectedPracticeBank"
    />
  </div>
</template>

<style scoped>
.favorite-button {
  color: #94a3b8;
  font-size: 20px !important;
  font-weight: 700;
}
.favorite-button.is-favorited {
  color: #f59e0b;
}
</style>
