<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useBankList } from '../composables/useBankList'
import { favoriteBank, unfavoriteBank } from '../api/v2/banks'
import AppPagination from './AppPagination.vue'
import AppLoading from './AppLoading.vue'
import AppEmpty from './AppEmpty.vue'
import AuthorSelect from './AuthorSelect.vue'
import TagSelectModal from './TagSelectModal.vue'
import BankCard from './bank/BankCard.vue'
import CreateBankModal from './bank/CreateBankModal.vue'
import AppButton from './AppButton.vue'
import type { QuestionBankV2 } from '../api/types'

const props = defineProps<{
  title: string; subtitle: string
  scope: 'mine' | 'public' | 'favorites'
  showAuthorFilter?: boolean; showVisibilityFilter?: boolean; showGenerationFilter?: boolean
  primaryLabel?: string; primaryTo?: string; allowCreate?: boolean
}>()

const route = useRoute()
const {
  banks, pageInfo, keyword, ownerId, selectedTags, visibility, generationStatus,
  loading, hasActiveFilters, load, applyFilters, clearAll, goPage,
} = useBankList(props.scope)

const tagModalOpen = ref(false)
const createOpen = ref(false)

function search() {
  const q: Record<string, string> = {}
  if (keyword.value.trim()) q.keyword = keyword.value.trim()
  if (ownerId.value) q.owner_id = String(ownerId.value)
  const tids = selectedTags.value.map(t => t.id).filter(Boolean).join(',')
  if (tids) q.tag_ids = tids
  if (visibility.value) q.visibility = visibility.value
  if (generationStatus.value) q.generation_status = generationStatus.value
  applyFilters({ keyword: keyword.value, ownerId: ownerId.value, selectedTags: selectedTags.value, visibility: visibility.value, generationStatus: generationStatus.value })
}

function selectTags(tags: typeof selectedTags.value) {
  selectedTags.value = tags
  search()
}

async function toggleFavorite(bank: QuestionBankV2) {
  const next = !bank.is_favorited
  bank.is_favorited = next
  try {
    if (next) await favoriteBank(bank.id)
    else await unfavoriteBank(bank.id)
  } catch { bank.is_favorited = !next }
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-5">
    <div class="p-4">
      <div class="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div>
          <h1 class="text-base font-semibold text-slate-900">{{ title }}</h1>
          <p class="text-sm text-slate-500">{{ subtitle }}</p>
        </div>
        <div class="flex gap-2">
          <AppButton v-if="allowCreate" size="sm" @click="createOpen = true">新建</AppButton>
          <RouterLink v-if="primaryTo" class="inline-flex items-center rounded-btn bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700" :to="primaryTo">{{ primaryLabel }}</RouterLink>
        </div>
      </div>

      <!-- Inline filter bar -->
      <div class="flex flex-wrap items-center gap-2">
        <input v-model="keyword" class="w-40 rounded-input border border-slate-300 bg-white px-2 py-1.5 text-sm" placeholder="搜索…" @keyup.enter="search" />
        <AuthorSelect v-if="showAuthorFilter" v-model="ownerId" @update:model-value="search()" />
        <AppButton variant="ghost" size="sm" @click="tagModalOpen = true">
          {{ selectedTags.length ? `标签 (${selectedTags.length})` : '标签' }}
        </AppButton>
        <select v-if="showVisibilityFilter" v-model="visibility" class="rounded-input border border-slate-300 bg-white px-2 py-1.5 text-sm" @change="search">
          <option value="">全部可见</option>
          <option value="private">私有</option>
          <option value="public">公开</option>
        </select>
        <select v-if="showGenerationFilter" v-model="generationStatus" class="rounded-input border border-slate-300 bg-white px-2 py-1.5 text-sm" @change="search">
          <option value="">全部状态</option>
          <option value="none">普通</option>
          <option value="processing">生成中</option>
          <option value="succeeded">成功</option>
          <option value="failed">失败</option>
        </select>
        <button v-if="hasActiveFilters" class="text-xs text-slate-400 hover:text-slate-600" @click="clearAll">清除筛选</button>
      </div>

      <!-- Active filter chips -->
      <div v-if="hasActiveFilters" class="mt-2 flex flex-wrap items-center gap-1 text-xs">
        <span v-if="keyword" class="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">{{ keyword }}</span>
        <span v-if="ownerId" class="rounded bg-slate-100 px-1.5 py-0.5 text-slate-600">作者</span>
        <span v-for="tag in selectedTags" :key="tag.id" class="rounded bg-brand-50 px-1.5 py-0.5 text-brand-700">{{ tag.name }}</span>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!banks.length" title="暂无题库" />

    <template v-else>
      <div class="divide-y divide-slate-100 border-y border-slate-200 px-4">
        <BankCard v-for="bank in banks" :key="bank.id" :bank="bank" @toggle-favorite="toggleFavorite(bank)" />
      </div>
      <AppPagination v-if="pageInfo && pageInfo.total_pages > 1" :page="pageInfo.page" :total-pages="pageInfo.total_pages" :total="pageInfo.total" @update:page="goPage" />
    </template>

    <TagSelectModal v-model="tagModalOpen" :selected="selectedTags" @update:selected="selectTags" />
    <CreateBankModal v-model="createOpen" @created="load()" />
  </section>
</template>
