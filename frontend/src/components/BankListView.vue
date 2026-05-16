<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page, type QuestionBank, type QuestionBankTag } from '../api/client'
import AppAvatar from './AppAvatar.vue'
import AppBadge from './AppBadge.vue'
import AppButton from './AppButton.vue'
import AppPagination from './AppPagination.vue'
import AppLoading from './AppLoading.vue'
import AppEmpty from './AppEmpty.vue'
import AppModal from './AppModal.vue'
import BankFilterModal from './BankFilterModal.vue'
import BankTagInput from './BankTagInput.vue'

const props = defineProps<{
  title: string
  subtitle: string
  endpoint: string
  showAuthorFilter?: boolean
  showVisibilityFilter?: boolean
  showGenerationFilter?: boolean
  primaryLabel?: string
  primaryTo?: string
  allowCreate?: boolean
}>()

const route = useRoute()
const router = useRouter()
const banks = ref<QuestionBank[]>([])
const pageInfo = ref<Page<QuestionBank> | null>(null)
const keyword = ref('')
const ownerId = ref<number | null>(null)
const selectedTags = ref<QuestionBankTag[]>([])
const visibility = ref('')
const generationStatus = ref('')
const loading = ref(false)
const filterOpen = ref(false)
const createModalOpen = ref(false)
const createTitle = ref('')
const createTags = ref<QuestionBankTag[]>([])
const creating = ref(false)

const totalPages = computed(() => pageInfo.value?.total_pages || 1)

function readQuery() {
  keyword.value = String(route.query.keyword || '')
  ownerId.value = route.query.owner_id ? Number(route.query.owner_id) : null
  visibility.value = String(route.query.visibility || '')
  generationStatus.value = String(route.query.generation_status || '')
}

async function syncTagsFromQuery() {
  const rawTagIds = String(route.query.tag_ids || '')
  const ids = rawTagIds.split(',').map(item => Number(item)).filter(Boolean)
  if (!ids.length) {
    selectedTags.value = []
    return
  }
  const currentIds = selectedTags.value.map(item => item.id).filter(Boolean).join(',')
  if (currentIds === ids.join(',')) return
  const params = new URLSearchParams({ ids: ids.join(','), page_size: '100' })
  selectedTags.value = (await api<Page<QuestionBankTag>>(`/api/v1/question-banks/tags?${params}`)).items
}

function buildQuery(page = Number(route.query.page || 1)) {
  const query: Record<string, string> = {}
  if (page > 1) query.page = String(page)
  if (keyword.value.trim()) query.keyword = keyword.value.trim()
  if (props.showAuthorFilter && ownerId.value) query.owner_id = String(ownerId.value)
  const tagIds = selectedTags.value.map(tag => tag.id).filter(Boolean)
  if (tagIds.length) query.tag_ids = tagIds.join(',')
  if (props.showVisibilityFilter && visibility.value) query.visibility = visibility.value
  if (props.showGenerationFilter && generationStatus.value) query.generation_status = generationStatus.value
  return query
}

async function load() {
  readQuery()
  await syncTagsFromQuery()
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (keyword.value.trim()) params.set('keyword', keyword.value.trim())
  if (props.showAuthorFilter && ownerId.value) params.set('owner_id', String(ownerId.value))
  const tagIds = selectedTags.value.map(tag => tag.id).filter(Boolean)
  if (tagIds.length) params.set('tag_ids', tagIds.join(','))
  if (props.showVisibilityFilter && visibility.value) params.set('visibility', visibility.value)
  if (props.showGenerationFilter && generationStatus.value) params.set('generation_status', generationStatus.value)
  loading.value = true
  try {
    const data = await api<Page<QuestionBank>>(`${props.endpoint}?${params}`)
    pageInfo.value = data
    banks.value = data.items
  } finally {
    loading.value = false
  }
}

function applyFilters(filters: { keyword: string; ownerId: number | null; selectedTags: QuestionBankTag[]; visibility: string; generationStatus: string }) {
  keyword.value = filters.keyword
  ownerId.value = filters.ownerId
  selectedTags.value = filters.selectedTags
  visibility.value = filters.visibility
  generationStatus.value = filters.generationStatus
  router.push({ query: buildQuery(1) })
}

function goPage(page: number) {
  router.push({ query: buildQuery(page) })
}

async function toggleFavorite(bank: QuestionBank) {
  await api(`/api/v1/question-banks/${bank.id}/favorite`, { method: bank.is_favorited ? 'DELETE' : 'POST' })
  await load()
}

async function doCreate() {
  if (!createTitle.value.trim()) return
  creating.value = true
  try {
    await api<QuestionBank>('/api/v1/question-banks', {
      method: 'POST',
      body: JSON.stringify({
        title: createTitle.value.trim(),
        visibility: 'private',
        tag_names: createTags.value.map(tag => tag.name),
      }),
    })
    createModalOpen.value = false
    createTitle.value = ''
    createTags.value = []
    await load()
  } finally {
    creating.value = false
  }
}

function statusText(bank: QuestionBank) {
  const visibilityText = bank.visibility === 'public' ? '公开' : '私有'
  const generationMap: Record<string, string> = {
    none: '普通题库', pending: '等待生成', processing: '生成中', succeeded: '生成成功', failed: '生成失败',
  }
  return `${visibilityText} · ${generationMap[bank.generation_status] || bank.generation_status}`
}

function statusVariant(status: string): 'default' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    none: 'default', pending: 'warning', processing: 'info', succeeded: 'success', failed: 'danger',
  }
  return map[status] || 'default'
}

const hasActiveFilters = computed(() =>
  keyword.value || ownerId.value || selectedTags.value.length || visibility.value || generationStatus.value
)

function clearAll() {
  keyword.value = ''
  ownerId.value = null
  selectedTags.value = []
  visibility.value = ''
  generationStatus.value = ''
  router.push({ query: {} })
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold">{{ title }}</h1>
          <p class="mt-1 text-slate-600">{{ subtitle }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <AppButton variant="ghost" @click="filterOpen = true">筛选</AppButton>
          <AppButton v-if="allowCreate" @click="createModalOpen = true">新建题库</AppButton>
          <RouterLink v-if="primaryTo" class="inline-flex items-center rounded-btn bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700" :to="primaryTo">{{ primaryLabel }}</RouterLink>
        </div>
      </div>
      <div v-if="hasActiveFilters" class="mt-3 flex flex-wrap items-center gap-1.5 text-xs">
        <span class="text-slate-400">已筛选：</span>
        <span v-if="keyword" class="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">"{{ keyword }}"</span>
        <span v-if="visibility" class="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">{{ visibility === 'public' ? '公开' : '私有' }}</span>
        <span v-if="generationStatus" class="rounded-full bg-slate-100 px-2 py-0.5 text-slate-600">{{ generationStatus }}</span>
        <span v-for="tag in selectedTags" :key="tag.id" class="rounded-full bg-brand-50 px-2 py-0.5 text-brand-700">{{ tag.name }}</span>
        <button class="text-brand-600 hover:text-brand-700" @click="clearAll">清除</button>
      </div>
    </div>

    <AppLoading v-if="loading" message="加载中…" />

    <template v-else-if="!banks.length">
      <AppEmpty title="暂无题库" :description="allowCreate ? '点击上方按钮创建第一个题库' : ''" />
    </template>

    <template v-else>
      <div class="grid gap-3">
        <article v-for="bank in banks" :key="bank.id" class="page-card p-5 transition-colors hover:border-brand-500/30">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <RouterLink class="min-w-0 flex-1" :to="`/banks/${bank.id}`">
              <div class="flex flex-wrap items-center gap-2">
                <h2 class="truncate text-lg font-semibold hover:text-brand-600">{{ bank.title }}</h2>
                <AppBadge :variant="statusVariant(bank.generation_status)">{{ statusText(bank) }}</AppBadge>
              </div>
              <p class="mt-2 line-clamp-2 text-sm text-slate-600">{{ bank.description || '暂无描述' }}</p>
              <div v-if="bank.tags.length" class="mt-3 flex flex-wrap gap-1.5">
                <span v-for="tag in bank.tags" :key="tag.id" class="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">{{ tag.name }}</span>
              </div>
            </RouterLink>
            <AppButton variant="ghost" size="sm" @click="toggleFavorite(bank)">
              {{ bank.is_favorited ? '已收藏' : '收藏' }}
            </AppButton>
          </div>

          <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
            <RouterLink class="flex min-w-0 items-center gap-2 hover:text-brand-600" :to="`/users/${bank.owner_id}`">
              <AppAvatar :src="bank.owner_avatar_url" :username="bank.owner_display_name || bank.owner_username" size="sm" />
              <span class="truncate">{{ bank.owner_display_name || bank.owner_username || `#${bank.owner_id}` }}</span>
            </RouterLink>
            <div class="flex flex-wrap gap-3">
              <span>{{ bank.question_count }} 题</span>
              <span>{{ bank.favorite_count }} 收藏</span>
              <span v-if="bank.ai_model_name">{{ bank.ai_model_name }}</span>
            </div>
          </div>
        </article>
      </div>

      <AppPagination
        v-if="pageInfo && pageInfo.total_pages > 1"
        :page="pageInfo.page"
        :total-pages="pageInfo.total_pages"
        :total="pageInfo.total"
        @update:page="goPage"
      />
    </template>

    <BankFilterModal
      v-model="filterOpen"
      :keyword="keyword"
      :owner-id="ownerId"
      :selected-tags="selectedTags"
      :visibility="visibility"
      :generation-status="generationStatus"
      :show-author-filter="showAuthorFilter"
      :show-visibility-filter="showVisibilityFilter"
      :show-generation-filter="showGenerationFilter"
      @apply="applyFilters"
    />

    <AppModal v-model="createModalOpen" title="新建题库" @update:model-value="val => !val && (createTitle = '', createTags = [])">
      <label class="block">
        <span class="mb-1 block text-sm font-medium text-slate-700">题库名称</span>
        <input v-model="createTitle" class="w-full rounded-input border border-slate-300 px-3 py-2 text-sm" placeholder="输入名称" @keyup.enter="doCreate" />
      </label>
      <div class="mt-4">
        <BankTagInput v-model="createTags" allow-create label="标签" />
      </div>
      <template #footer>
        <AppButton variant="ghost" @click="createModalOpen = false">取消</AppButton>
        <AppButton :loading="creating" :disabled="!createTitle.trim()" @click="doCreate">创建</AppButton>
      </template>
    </AppModal>
  </section>
</template>
