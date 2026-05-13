<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type Page, type QuestionBank } from '../api/client'
import AuthorSelect from './AuthorSelect.vue'

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
const visibility = ref('')
const generationStatus = ref('')
const loading = ref(false)

const totalPages = computed(() => pageInfo.value?.total_pages || 1)

function readQuery() {
  keyword.value = String(route.query.keyword || '')
  ownerId.value = route.query.owner_id ? Number(route.query.owner_id) : null
  visibility.value = String(route.query.visibility || '')
  generationStatus.value = String(route.query.generation_status || '')
}

function buildQuery(page = Number(route.query.page || 1)) {
  const query: Record<string, string> = {}
  if (page > 1) query.page = String(page)
  if (keyword.value.trim()) query.keyword = keyword.value.trim()
  if (props.showAuthorFilter && ownerId.value) query.owner_id = String(ownerId.value)
  if (props.showVisibilityFilter && visibility.value) query.visibility = visibility.value
  if (props.showGenerationFilter && generationStatus.value) query.generation_status = generationStatus.value
  return query
}

async function load() {
  readQuery()
  const params = new URLSearchParams()
  params.set('page', String(route.query.page || 1))
  if (keyword.value.trim()) params.set('keyword', keyword.value.trim())
  if (props.showAuthorFilter && ownerId.value) params.set('owner_id', String(ownerId.value))
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

function search() {
  router.push({ query: buildQuery(1) })
}

function clearFilters() {
  keyword.value = ''
  ownerId.value = null
  visibility.value = ''
  generationStatus.value = ''
  router.push({ query: {} })
}

function goPage(page: number) {
  router.push({ query: buildQuery(page) })
}

async function toggleFavorite(bank: QuestionBank) {
  await api(`/api/v1/question-banks/${bank.id}/favorite`, { method: bank.is_favorited ? 'DELETE' : 'POST' })
  await load()
}

async function createBank() {
  const title = prompt('题库名称')
  if (!title?.trim()) return
  await api<QuestionBank>('/api/v1/question-banks', { method: 'POST', body: JSON.stringify({ title: title.trim(), visibility: 'private' }) })
  await load()
}

function statusText(bank: QuestionBank) {
  const visibilityText = bank.visibility === 'public' ? '公开' : '私有'
  const generationMap: Record<string, string> = {
    none: '普通题库',
    pending: '等待生成',
    processing: '生成中',
    succeeded: '生成成功',
    failed: '生成失败',
  }
  return `${visibilityText} · ${generationMap[bank.generation_status] || bank.generation_status}`
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="grid gap-5">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold">{{ title }}</h1>
          <p class="mt-1 text-slate-600">{{ subtitle }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button v-if="allowCreate" class="rounded-md bg-slate-900 px-4 py-2 text-white" type="button" @click="createBank">新建题库</button>
          <RouterLink v-if="primaryTo" class="rounded-md bg-blue-600 px-4 py-2 text-white" :to="primaryTo">{{ primaryLabel }}</RouterLink>
        </div>
      </div>

      <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <label class="block">
          <span class="mb-1 block text-xs font-medium text-slate-500">关键词</span>
          <input v-model="keyword" class="w-full rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="标题或描述" @keyup.enter="search" />
        </label>
        <AuthorSelect v-if="showAuthorFilter" v-model="ownerId" />
        <label v-if="showVisibilityFilter" class="block">
          <span class="mb-1 block text-xs font-medium text-slate-500">可见性</span>
          <select v-model="visibility" class="w-full rounded-md border border-slate-300 bg-white px-3 py-2">
            <option value="">全部</option>
            <option value="private">私有</option>
            <option value="public">公开</option>
          </select>
        </label>
        <label v-if="showGenerationFilter" class="block">
          <span class="mb-1 block text-xs font-medium text-slate-500">生成状态</span>
          <select v-model="generationStatus" class="w-full rounded-md border border-slate-300 bg-white px-3 py-2">
            <option value="">全部</option>
            <option value="none">普通题库</option>
            <option value="pending">等待生成</option>
            <option value="processing">生成中</option>
            <option value="succeeded">生成成功</option>
            <option value="failed">生成失败</option>
          </select>
        </label>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <button class="rounded-md bg-slate-900 px-4 py-2 text-white" type="button" @click="search">筛选</button>
        <button class="rounded-md bg-slate-100 px-4 py-2 text-slate-700" type="button" @click="clearFilters">清空</button>
      </div>
    </div>

    <div class="grid gap-3">
      <article v-for="bank in banks" :key="bank.id" class="rounded-xl border border-slate-200 bg-white p-5 hover:border-blue-300">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <RouterLink class="min-w-0 flex-1" :to="`/banks/${bank.id}`">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="truncate text-lg font-semibold">{{ bank.title }}</h2>
              <span class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{{ statusText(bank) }}</span>
            </div>
            <p class="mt-2 line-clamp-2 text-sm text-slate-600">{{ bank.description || '暂无描述' }}</p>
          </RouterLink>
          <button class="rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700 hover:bg-slate-200" type="button" @click="toggleFavorite(bank)">
            {{ bank.is_favorited ? '已收藏' : '收藏' }}
          </button>
        </div>

        <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
          <RouterLink class="flex min-w-0 items-center gap-2 hover:text-blue-700" :to="`/users/${bank.owner_id}`">
            <img v-if="bank.owner_avatar_url" class="h-8 w-8 rounded-full object-cover" :src="bank.owner_avatar_url" alt="" />
            <span v-else class="grid h-8 w-8 place-items-center rounded-full bg-slate-800 text-xs font-bold text-white">{{ (bank.owner_display_name || bank.owner_username || 'U').slice(0, 1).toUpperCase() }}</span>
            <span class="truncate">{{ bank.owner_display_name || bank.owner_username || `#${bank.owner_id}` }}</span>
          </RouterLink>
          <div class="flex flex-wrap gap-3">
            <span>{{ bank.question_count }} 题</span>
            <span>{{ bank.favorite_count }} 收藏</span>
            <span v-if="bank.ai_model_name">{{ bank.ai_model_name }}</span>
          </div>
        </div>
      </article>
      <div v-if="!banks.length && !loading" class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500">暂无题库</div>
    </div>

    <div v-if="pageInfo" class="flex flex-wrap items-center justify-end gap-3 text-sm text-slate-600">
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page <= 1" @click="goPage(pageInfo.page - 1)">上一页</button>
      <span>第 {{ pageInfo.page }} / {{ totalPages }} 页，共 {{ pageInfo.total }} 个</span>
      <button class="rounded-md bg-slate-200 px-3 py-2 text-slate-900 disabled:opacity-50" :disabled="pageInfo.page >= totalPages" @click="goPage(pageInfo.page + 1)">下一页</button>
    </div>
  </section>
</template>
