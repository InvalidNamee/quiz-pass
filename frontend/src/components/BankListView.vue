<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBankList } from '../composables/useBankList'
import { ElMessageBox } from 'element-plus'
import { favoriteBank, unfavoriteBank, shareBank, deleteBank } from '../api/v2/banks'
import type { QuestionBankV2 } from '../api/types'
import GenerateBankDialog from './GenerateBankDialog.vue'
import PracticeSetupDialog from './PracticeSetupDialog.vue'
import TagFilterDialog from './TagFilterDialog.vue'
import AuthorFilterDialog from './AuthorFilterDialog.vue'
import { Rocket, Star, Zap, Share2, Trash2, Plus } from '@lucide/vue'
import { isUnstableBankStatus, isUnstableWorkflowStatus } from '../utils/generationStatus'
import { useToast } from '../composables/useToast'
import { practiceProgressColor, practiceProgressPercent, practiceProgressText, practiceProgressType } from '../utils/practiceProgress'

const props = defineProps<{
  title: string; subtitle: string
  scope: 'mine' | 'public' | 'favorites'
  showAuthorFilter?: boolean; showVisibilityFilter?: boolean; showGenerationFilter?: boolean
  allowCreate?: boolean
}>()

const route = useRoute()
const router = useRouter()
const { banks, pageInfo, keyword, selectedAuthor, selectedTags, visibility, generationStatus, loading, hasActiveFilters, load, clearAll, goPage } = useBankList(props.scope)
const toast = useToast()
const viewMode = ref<string>(localStorage.getItem('qp-view-mode') || 'grid')

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
  try {
    if (next) await favoriteBank(bank.id)
    else await unfavoriteBank(bank.id)
    bank.stats.favorite_count = Math.max(0, bank.stats.favorite_count + (next ? 1 : -1))
    toast.show(next ? '已收藏题库' : '已取消收藏', 'success')
  } catch (err) {
    bank.is_favorited = !next
    toast.show(err instanceof Error ? err.message : '收藏操作失败', 'error')
  }
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
  router.push(`/practice/session/${bank.resumable_session.id}?resume=1`)
}

async function handleShare(bank: QuestionBankV2) {
  ElMessageBox.confirm(
    '公开分享将创建一个完全公开且只读的题库副本。其他社区用户可以浏览并自由练习该副本，但除管理员之外的任何人均无权对其进行编辑。您确定要公开分享吗？',
    '公开分享题库',
    {
      confirmButtonText: '确定分享',
      cancelButtonText: '取消',
      type: 'info',
    }
  ).then(async () => {
    try {
      const shared = await shareBank(bank.id)
      toast.show(`已生成公开副本「${shared.title}」`, 'success')
      await load()
    } catch (err) {
      toast.show(err instanceof Error ? err.message : '分享失败', 'error')
    }
  }).catch(() => {})
}

function handleDelete(bank: QuestionBankV2) {
  ElMessageBox.confirm(`确定要删除「${bank.title}」吗？`, '删除题库', {
    confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning',
  }).then(async () => {
    try {
      await deleteBank(bank.id)
      toast.show('题库已删除', 'success')
      await load()
    } catch (err) {
      toast.show(err instanceof Error ? err.message : '删除失败', 'error')
    }
  }).catch(() => {})
}

onMounted(load)
watch(() => route.fullPath, () => { void load() })
  watch(viewMode, (v) => {
    localStorage.setItem('qp-view-mode', v)
  })
watch(banks, syncPolling, { deep: true })
onBeforeUnmount(stopPolling)
</script>

<template>
  <div class="qp-page space-y-4">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title !text-xl !font-bold bg-gradient-to-r from-slate-900 to-indigo-950 bg-clip-text text-transparent">{{ title }}</h1>
        <p class="qp-subtitle">{{ subtitle }}</p>
      </div>
      <div class="flex gap-2">
        <el-button
          v-if="allowCreate"
          size="small"
          type="primary"
          class="!rounded-xl !bg-gradient-to-r !from-indigo-500 !to-purple-500 !border-none !h-9 shadow-md shadow-indigo-500/10 active:scale-95 transition-all"
          @click="createDialogVisible = true"
        >
          <Plus :size="14" class="mr-1" />新建题库
        </el-button>
      </div>
    </div>

    <!-- Inline filters -->
    <div class="qp-toolbar !border-none bg-white p-3 rounded-2xl shadow-sm border border-slate-100 flex flex-wrap gap-2.5 items-center">
      <el-input v-model="keyword" size="small" placeholder="搜索题库…" clearable class="!w-48" @change="applySearch" />
      <AuthorFilterDialog v-if="showAuthorFilter" v-model="selectedAuthor" @update:model-value="applySearch" />
      <TagFilterDialog v-model="selectedTags" @update:model-value="applySearch" />

      <el-select v-if="showVisibilityFilter" v-model="visibility" size="small" placeholder="可见性" clearable class="!w-24" @change="applySearch">
        <el-option label="私有" value="private" />
        <el-option label="公开" value="public" />
      </el-select>

      <el-select v-if="showGenerationFilter" v-model="generationStatus" size="small" placeholder="生成状态" clearable class="!w-28" @change="applySearch">
        <el-option label="手动创建" value="none" />
        <el-option label="生成中" value="processing" />
        <el-option label="成功" value="succeeded" />
        <el-option label="失败" value="failed" />
      </el-select>

      <el-button v-if="hasActiveFilters" size="small" text class="!text-slate-400 hover:!text-indigo-600" @click="clearAll">清除筛选</el-button>

      <el-radio-group v-model="viewMode" size="small" @change="applySearch" class="ml-auto !shadow-sm !rounded-lg overflow-hidden">
        <el-radio-button value="table">表格</el-radio-button>
        <el-radio-button value="grid">网格</el-radio-button>
      </el-radio-group>
    </div>

    <div v-if="selectedTags.length || (showAuthorFilter && selectedAuthor)" class="flex flex-wrap items-center gap-2 bg-slate-50/50 p-2.5 rounded-xl border border-slate-100">
      <template v-if="showAuthorFilter && selectedAuthor">
        <span class="text-xs font-semibold text-slate-400 tracking-wider">已选作者</span>
        <el-tag closable size="small" type="primary" effect="plain" class="!rounded-lg" @close="selectedAuthor = null; applySearch()">
          {{ selectedAuthor.display_name || selectedAuthor.username }}
        </el-tag>
      </template>
      <template v-if="selectedTags.length">
        <span v-if="!(showAuthorFilter && selectedAuthor)" class="text-xs font-semibold text-slate-400 tracking-wider">已选标签</span>
        <el-tag v-for="tag in selectedTags" :key="tag.id" closable size="small" type="primary" effect="plain" class="!rounded-lg" @close="selectedTags = selectedTags.filter(t => t.id !== tag.id); applySearch()">
          {{ tag.name }}
        </el-tag>
      </template>
    </div>

    <!-- Table View -->
    <el-table
      v-if="viewMode === 'table'"
      v-loading="loading"
      :data="banks"
      stripe
      size="small"
      highlight-current-row
      class="border border-slate-100 !rounded-2xl shadow-sm"
    >
      <el-table-column label="题库名称" min-width="220">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <div class="flex flex-col py-1">
            <div class="flex items-center gap-2">
              <button
                class="inline-flex h-8 w-8 items-center justify-center rounded-lg border transition-all active:scale-95"
                :class="row.is_favorited ? 'border-amber-200 bg-amber-50 text-amber-500 hover:bg-amber-100' : 'border-slate-200 bg-slate-50 text-slate-300 hover:border-amber-200 hover:bg-amber-50 hover:text-amber-400'"
                @click.stop="toggleFavorite(row)"
              >
                <Star :size="16" :fill="row.is_favorited ? '#f59e0b' : 'none'" :stroke="row.is_favorited ? '#f59e0b' : 'currentColor'" />
              </button>
              <RouterLink
                class="font-semibold text-slate-800 text-[14px] hover:text-indigo-600 hover:underline"
                :to="`/banks/${row.id}`"
                @click.stop
              >
                {{ row.title }}
              </RouterLink>
              <el-tag size="small" class="!rounded-md" :type="row.visibility === 'public' ? 'success' : 'info'">
                {{ row.visibility === 'public' ? '公开' : '私有' }}
              </el-tag>
            </div>
            <span v-if="row.description" class="text-xs text-slate-400 truncate max-w-xs mt-1">{{ row.description }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="标签" width="180">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <div class="flex flex-wrap gap-1">
            <el-tag v-for="tag in row.tags.slice(0, 3)" :key="tag.id" size="small" type="info" class="!rounded-md !bg-slate-50 !border-slate-100 !text-slate-500">{{ tag.name }}</el-tag>
            <span v-if="row.tags.length > 3" class="text-[10px] text-slate-400 font-bold bg-slate-100/60 px-1 py-0.5 rounded">+{{ row.tags.length - 3 }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="所有者" width="120">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <RouterLink class="text-indigo-600 font-semibold hover:text-indigo-500 hover:underline" :to="`/users/${row.owner.id}`" @click.stop>
            {{ row.owner.display_name || row.owner.username }}
          </RouterLink>
        </template>
      </el-table-column>
      <el-table-column label="题目" width="60" align="center">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <span class="font-bold text-slate-700">{{ row.stats.question_count }}</span>
        </template>
      </el-table-column>
      <el-table-column label="收藏" width="60" align="center">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <span class="text-slate-400">{{ row.stats.favorite_count }}</span>
        </template>
      </el-table-column>
      <el-table-column label="最近进度" width="190">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <div v-if="row.latest_practice_session" class="grid gap-1">
            <div class="flex items-center justify-between gap-2 text-xs">
              <span class="font-semibold text-slate-500">{{ practiceProgressType(row.latest_practice_session) }}</span>
              <span class="text-slate-400">{{ practiceProgressText(row.latest_practice_session) }}</span>
            </div>
            <el-progress
              :percentage="practiceProgressPercent(row.latest_practice_session)"
              :color="practiceProgressColor(row.latest_practice_session)"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
          <span v-else class="text-xs text-slate-300">—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="210" align="right">
        <template #default="{ row }: { row: QuestionBankV2 }">
          <div class="qp-icon-actions">
            <el-tooltip v-if="row.resumable_session" content="继续练习" placement="top">
              <el-button size="small" class="qp-icon-button is-blue" @click.stop="continuePractice(row)">
                <Zap :size="16" />
              </el-button>
            </el-tooltip>
            <el-tooltip v-if="row.permissions.can_practice" content="开始练习" placement="top">
              <el-button size="small" class="qp-icon-button" @click.stop="openPractice(row)">
                <Rocket :size="16" />
              </el-button>
            </el-tooltip>
            <el-tooltip v-if="row.permissions.can_share" content="分享题库" placement="top">
              <el-button size="small" class="qp-icon-button is-blue" @click.stop="handleShare(row)">
                <Share2 :size="16" />
              </el-button>
            </el-tooltip>
            <el-tooltip v-if="row.permissions.can_manage" content="删除题库" placement="top">
              <el-button size="small" class="qp-icon-button is-red" @click.stop="handleDelete(row)">
                <Trash2 :size="16" />
              </el-button>
            </el-tooltip>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- Grid View -->
    <div v-if="viewMode === 'grid'" v-loading="loading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div
        v-for="bank in banks"
        :key="bank.id"
        class="group flex flex-col gap-2.5 rounded-2xl border border-slate-100 bg-white p-4.5 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:border-indigo-500/10"
      >
        <div class="flex items-start justify-between gap-2">
          <div class="flex flex-1 items-center gap-1.5 min-w-0">
            <button
              class="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-all active:scale-95"
              :class="bank.is_favorited ? 'border-amber-200 bg-amber-50 text-amber-500 hover:bg-amber-100' : 'border-slate-200 bg-slate-50 text-slate-300 hover:border-amber-200 hover:bg-amber-50 hover:text-amber-400'"
              @click.stop="toggleFavorite(bank)"
            >
              <Star :size="16" :fill="bank.is_favorited ? '#f59e0b' : 'none'" :stroke="bank.is_favorited ? '#f59e0b' : 'currentColor'" />
            </button>
            <RouterLink
              class="truncate text-[14px] font-bold text-slate-800 transition-colors hover:text-indigo-600 hover:underline"
              :to="`/banks/${bank.id}`"
              @click.stop
            >
              {{ bank.title }}
            </RouterLink>
          </div>
          <div class="flex shrink-0 items-center gap-1">
            <el-tag size="small" class="!rounded-md" :type="bank.visibility === 'public' ? 'success' : 'info'">
              {{ bank.visibility === 'public' ? '公开' : '私有' }}
            </el-tag>
            <el-tag v-if="bank.is_shared_copy" size="small" class="!rounded-md" type="info">副本</el-tag>
          </div>
        </div>

        <p v-if="bank.description" class="text-xs text-slate-400 line-clamp-2 mt-0.5 leading-relaxed">{{ bank.description }}</p>

        <div v-if="bank.tags.length" class="flex flex-wrap gap-1 mt-1">
          <el-tag v-for="tag in bank.tags.slice(0, 3)" :key="tag.id" size="small" type="info" class="!rounded-md !bg-slate-50 !border-slate-100 !text-slate-500">{{ tag.name }}</el-tag>
          <span v-if="bank.tags.length > 3" class="text-[10px] text-slate-400 font-bold bg-slate-100/60 px-1 py-0.5 rounded">+{{ bank.tags.length - 3 }}</span>
        </div>

        <div v-if="bank.latest_practice_session" class="grid gap-1.5 rounded-xl bg-slate-50/70 px-2.5 py-2">
          <div class="flex items-center justify-between gap-2 text-xs">
            <span class="font-semibold text-slate-500">{{ practiceProgressType(bank.latest_practice_session) }}</span>
            <span class="text-slate-400">{{ practiceProgressText(bank.latest_practice_session) }}</span>
          </div>
          <el-progress
            :percentage="practiceProgressPercent(bank.latest_practice_session)"
            :color="practiceProgressColor(bank.latest_practice_session)"
            :stroke-width="7"
            :show-text="false"
          />
        </div>

        <div class="flex items-center justify-between text-xs text-slate-400 border-t border-slate-50 pt-2.5 mt-1.5 font-medium">
          <RouterLink :to="`/users/${bank.owner.id}`" class="truncate hover:text-indigo-600 hover:underline" @click.stop>
            {{ bank.owner.display_name || bank.owner.username }}
          </RouterLink>
          <div class="flex items-center gap-2 shrink-0">
            <span>{{ bank.stats.question_count }} 题</span>
            <span><Star :size="10" class="inline mr-0.5 text-amber-500" />{{ bank.stats.favorite_count }} 收藏</span>
          </div>
        </div>

        <div class="mt-2.5 flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-50">
          <el-tooltip v-if="bank.resumable_session" content="继续练习" placement="top">
            <el-button size="small" class="qp-icon-button is-blue" @click.stop="continuePractice(bank)">
              <Zap :size="16" />
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="bank.permissions.can_practice" content="开始练习" placement="top">
            <el-button size="small" class="qp-icon-button" @click.stop="openPractice(bank)">
              <Rocket :size="16" />
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="bank.permissions.can_share" content="分享题库" placement="top">
            <el-button size="small" class="qp-icon-button is-blue" @click.stop="handleShare(bank)">
              <Share2 :size="16" />
            </el-button>
          </el-tooltip>
          <el-tooltip v-if="bank.permissions.can_manage" content="删除题库" placement="top">
            <el-button size="small" class="qp-icon-button is-red ml-auto" @click.stop="handleDelete(bank)">
              <Trash2 :size="16" />
            </el-button>
          </el-tooltip>
        </div>
      </div>
    </div>

    <el-empty v-if="viewMode === 'grid' && !loading && !banks.length" description="没有匹配的题库" />

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
