import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as v2 from '../api/v2/banks'
import type { Page, QuestionBankV2, QuestionBankTag } from '../api/types'

export function useBankList(scope: 'mine' | 'public' | 'favorites') {
  const route = useRoute()
  const router = useRouter()

  const banks = ref<QuestionBankV2[]>([])
  const pageInfo = ref<Page<QuestionBankV2> | null>(null)
  const keyword = ref('')
  const ownerId = ref<number | null>(null)
  const selectedTags = ref<QuestionBankTag[]>([])
  const visibility = ref('')
  const generationStatus = ref('')
  const loading = ref(false)

  const hasActiveFilters = computed(() =>
    keyword.value || ownerId.value || selectedTags.value.length || visibility.value || generationStatus.value
  )

  function readQuery() {
    keyword.value = String(route.query.keyword || '')
    ownerId.value = route.query.owner_id ? Number(route.query.owner_id) : null
    visibility.value = String(route.query.visibility || '')
    generationStatus.value = String(route.query.generation_status || '')
  }

  async function syncTagsFromQuery() {
    const ids = String(route.query.tag_ids || '').split(',').map(Number).filter(Boolean)
    if (!ids.length) { selectedTags.value = []; return }
    const curIds = selectedTags.value.map(t => t.id).filter(Boolean).join(',')
    if (curIds === ids.join(',')) return
    selectedTags.value = (await v2.listTags({ ids: ids.join(','), page_size: 100 })).items
  }

  function buildQuery(page = Number(route.query.page || 1)) {
    const q: Record<string, string> = {}
    if (page > 1) q.page = String(page)
    if (keyword.value.trim()) q.keyword = keyword.value.trim()
    if (ownerId.value) q.owner_id = String(ownerId.value)
    const tids = selectedTags.value.map(t => t.id).filter(Boolean).join(',')
    if (tids) q.tag_ids = tids
    if (visibility.value) q.visibility = visibility.value
    if (generationStatus.value) q.generation_status = generationStatus.value
    return q
  }

  async function load() {
    readQuery()
    await syncTagsFromQuery()
    const params = buildQuery(Number(route.query.page || 1))
    params.page = params.page || '1'
    loading.value = true
    try {
      const data = await v2.listBanks(scope, params)
      pageInfo.value = data as unknown as Page<QuestionBankV2>
      banks.value = data.items
    } finally { loading.value = false }
  }

  function applyFilters(filters: { keyword: string; ownerId: number | null; selectedTags: QuestionBankTag[]; visibility: string; generationStatus: string }) {
    keyword.value = filters.keyword; ownerId.value = filters.ownerId
    selectedTags.value = filters.selectedTags; visibility.value = filters.visibility
    generationStatus.value = filters.generationStatus
    router.push({ query: buildQuery(1) })
  }

  function clearAll() {
    keyword.value = ''; ownerId.value = null; selectedTags.value = []
    visibility.value = ''; generationStatus.value = ''
    router.push({ query: {} })
  }

  function goPage(page: number) { router.push({ query: buildQuery(page) }) }

  return {
    banks, pageInfo, keyword, ownerId, selectedTags, visibility, generationStatus,
    loading, hasActiveFilters, load, applyFilters, clearAll, goPage,
  }
}
