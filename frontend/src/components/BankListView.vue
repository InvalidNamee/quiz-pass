<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useBankList } from '../composables/useBankList'
import { favoriteBank, unfavoriteBank } from '../api/v2/banks'
import AppPagination from './AppPagination.vue'
import AppLoading from './AppLoading.vue'
import AppEmpty from './AppEmpty.vue'
import BankFilterModal from './BankFilterModal.vue'
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

const filterOpen = ref(false)
const createOpen = ref(false)

async function toggleFavorite(bank: QuestionBankV2) {
  if (bank.is_favorited) await unfavoriteBank(bank.id)
  else await favoriteBank(bank.id)
  await load()
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card p-4">
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 class="text-lg font-bold">{{ title }}</h1>
          <p class="text-sm text-slate-500">{{ subtitle }}</p>
        </div>
        <div class="flex gap-2">
          <AppButton variant="ghost" size="sm" @click="filterOpen = true">筛选</AppButton>
          <AppButton v-if="allowCreate" size="sm" @click="createOpen = true">新建</AppButton>
          <RouterLink v-if="primaryTo" class="inline-flex items-center rounded-btn bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700" :to="primaryTo">{{ primaryLabel }}</RouterLink>
        </div>
      </div>
      <div v-if="hasActiveFilters" class="mt-2 flex flex-wrap items-center gap-1 text-xs">
        <span class="text-slate-400">筛选：</span>
        <span v-if="keyword" class="rounded-full bg-slate-100 px-1.5 py-0.5">"{{ keyword }}"</span>
        <span v-if="visibility" class="rounded-full bg-slate-100 px-1.5 py-0.5">{{ visibility === 'public' ? '公开' : '私有' }}</span>
        <span v-for="tag in selectedTags" :key="tag.id" class="rounded-full bg-brand-50 px-1.5 py-0.5 text-brand-700">{{ tag.name }}</span>
        <button class="text-brand-600 hover:text-brand-700" @click="clearAll">清除</button>
      </div>
    </div>

    <AppLoading v-if="loading" />
    <AppEmpty v-else-if="!banks.length" title="暂无题库" />

    <template v-else>
      <div class="grid gap-2">
        <BankCard v-for="bank in banks" :key="bank.id" :bank="bank" @toggle-favorite="toggleFavorite(bank)" />
      </div>
      <AppPagination v-if="pageInfo && pageInfo.total_pages > 1" :page="pageInfo.page" :total-pages="pageInfo.total_pages" :total="pageInfo.total" @update:page="goPage" />
    </template>

    <BankFilterModal v-model="filterOpen" :keyword="keyword" :owner-id="ownerId" :selected-tags="selectedTags" :visibility="visibility" :generation-status="generationStatus" :show-author-filter="showAuthorFilter" :show-visibility-filter="showVisibilityFilter" :show-generation-filter="showGenerationFilter" @apply="applyFilters" />
    <CreateBankModal v-model="createOpen" @created="load()" />
  </section>
</template>
