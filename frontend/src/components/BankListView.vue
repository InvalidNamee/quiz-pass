<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useBankList } from '../composables/useBankList'
import { favoriteBank, unfavoriteBank, listTags } from '../api/v2/banks'
import type { QuestionBankV2, QuestionBankTag } from '../api/types'
import GenerateBankDialog from './GenerateBankDialog.vue'
import { isUnstableBankStatus, isUnstableWorkflowStatus } from '../utils/generationStatus'

const props = defineProps<{
  title: string; subtitle: string
  scope: 'mine' | 'public' | 'favorites'
  showAuthorFilter?: boolean; showVisibilityFilter?: boolean; showGenerationFilter?: boolean
  allowCreate?: boolean
}>()

const route = useRoute()
const router = useRouter()
const { banks, pageInfo, keyword, ownerId, selectedTags, visibility, generationStatus, loading, hasActiveFilters, load, clearAll, goPage } = useBankList(props.scope)

const tagDialogVisible = ref(false)
const createDialogVisible = ref(false)
const allTags = ref<QuestionBankTag[]>([])
const selectedTagIds = ref<number[]>([])
const tagKeyword = ref('')
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
  if (props.showAuthorFilter && ownerId.value) q.owner_id = String(ownerId.value)
  const tids = selectedTags.value.map(t => t.id).filter(Boolean).join(',')
  if (tids) q.tag_ids = tids
  if (visibility.value) q.visibility = visibility.value
  if (generationStatus.value) q.generation_status = generationStatus.value
  router.push({ query: q })
}

async function loadTagOptions() {
  allTags.value = (await listTags({ keyword: tagKeyword.value.trim() || undefined, page_size: 200 })).items
}

async function openTagDialog() {
  tagKeyword.value = ''
  await loadTagOptions()
  selectedTagIds.value = selectedTags.value.map(t => t.id)
  tagDialogVisible.value = true
}

function toggleTag(tag: QuestionBankTag) {
  const idx = selectedTagIds.value.indexOf(tag.id)
  if (idx >= 0) selectedTagIds.value.splice(idx, 1)
  else selectedTagIds.value.push(tag.id)
}

function confirmTags() {
  const merged = [...selectedTags.value, ...allTags.value]
  selectedTags.value = selectedTagIds.value
    .map(id => merged.find(t => t.id === id))
    .filter((tag): tag is QuestionBankTag => Boolean(tag))
  tagDialogVisible.value = false
  applySearch()
}

function removeSelectedTag(tagId: number) {
  selectedTags.value = selectedTags.value.filter(t => t.id !== tagId)
  applySearch()
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
      <el-input v-if="showAuthorFilter" v-model.number="ownerId" size="small" placeholder="作者ID" clearable class="!w-24" @change="applySearch" />
      <el-button size="small" @click="openTagDialog">{{ selectedTags.length ? `标签(${selectedTags.length})` : '标签' }}</el-button>
      <el-select v-if="showVisibilityFilter" v-model="visibility" size="small" placeholder="可见性" clearable class="!w-24" @change="applySearch">
        <el-option label="私有" value="private" />
        <el-option label="公开" value="public" />
      </el-select>
      <el-select v-if="showGenerationFilter" v-model="generationStatus" size="small" placeholder="状态" clearable class="!w-24" @change="applySearch">
        <el-option label="普通" value="none" />
        <el-option label="生成中" value="processing" />
        <el-option label="成功" value="succeeded" />
        <el-option label="失败" value="failed" />
      </el-select>
      <el-button v-if="hasActiveFilters" size="small" text @click="clearAll">清除</el-button>
    </div>
    <div v-if="selectedTags.length" class="flex flex-wrap items-center gap-2 border-b border-slate-100 pb-2">
      <span class="text-sm text-slate-500">已选标签</span>
      <el-tag v-for="tag in selectedTags" :key="tag.id" closable size="small" type="primary" effect="plain" @close="removeSelectedTag(tag.id)">
        {{ tag.name }}
      </el-tag>
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
      <el-table-column label="题" width="50" align="center">
        <template #default="{ row }: { row: QuestionBankV2 }">{{ row.stats.question_count }}</template>
      </el-table-column>
      <el-table-column label="收藏" width="50" align="center">
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

    <!-- Tag dialog -->
    <el-dialog v-model="tagDialogVisible" title="选择标签" width="420px">
      <div class="mb-3 flex gap-2">
        <el-input v-model="tagKeyword" placeholder="搜索标签" clearable @keyup.enter="loadTagOptions" @clear="loadTagOptions" />
        <el-button @click="loadTagOptions">搜索</el-button>
      </div>
      <div class="flex max-h-80 flex-wrap gap-2 overflow-y-auto">
        <el-tag v-for="tag in allTags" :key="tag.id" :type="selectedTagIds.includes(tag.id) ? 'primary' : 'info'" class="cursor-pointer" @click="toggleTag(tag)">{{ tag.name }}</el-tag>
      </div>
      <p v-if="!allTags.length" class="py-4 text-center text-sm text-slate-400">暂无标签</p>
      <template #footer>
        <el-button @click="tagDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmTags">确定 ({{ selectedTagIds.length }})</el-button>
      </template>
    </el-dialog>

    <GenerateBankDialog v-model="createDialogVisible" @submitted="load" />
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
