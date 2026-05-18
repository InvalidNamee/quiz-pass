<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBank, updateBank, deleteBank, favoriteBank, unfavoriteBank, exportBankUrl } from '../api/v2/banks'
import type { QuestionBankV2, QuestionBankTag } from '../api/types'
import { useAuthStore } from '../stores/auth'
import AppBadge from '../components/AppBadge.vue'
import AppButton from '../components/AppButton.vue'
import AppAvatar from '../components/AppAvatar.vue'
import AppModal from '../components/AppModal.vue'
import AppLoading from '../components/AppLoading.vue'
import BankTagInput from '../components/BankTagInput.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const bank = ref<QuestionBankV2 | null>(null)
const loading = ref(true)
const editing = ref(false)
const deleteModal = ref(false)
const editForm = ref({ title: '', description: '', visibility: 'private' })
const editTags = ref<QuestionBankTag[]>([])
const editIsPublic = computed({
  get: () => editForm.value.visibility === 'public',
  set: (val: boolean) => { editForm.value.visibility = val ? 'public' : 'private' },
})
const canManage = computed(() => bank.value?.permissions.can_manage ?? false)
const saving = ref(false)
const deleting = ref(false)
const exporting = ref(false)

async function load() {
  loading.value = true
  try {
    bank.value = await getBank(Number(route.params.bankId))
    editForm.value = {
      title: bank.value.title,
      description: bank.value.description || '',
      visibility: bank.value.visibility,
    }
    editTags.value = bank.value.tags || []
  } finally { loading.value = false }
}

async function favorite() {
  if (!bank.value) return
  if (bank.value.is_favorited) await unfavoriteBank(bank.value.id)
  else await favoriteBank(bank.value.id)
  await load()
}

async function saveEdit() {
  if (!bank.value) return
  saving.value = true
  try {
    await updateBank(bank.value.id, { ...editForm.value, tag_names: editTags.value.map(t => t.name) })
    editing.value = false
    toast.show('题库已更新', 'success')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  } finally { saving.value = false }
}

async function removeBank() {
  if (!bank.value) return
  deleting.value = true
  try {
    await deleteBank(bank.value.id)
    deleteModal.value = false
    router.push('/banks')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '删除失败', 'error')
  } finally { deleting.value = false }
}

async function exportJson() {
  if (!bank.value) return
  exporting.value = true
  try {
    const resp = await fetch(exportBankUrl(bank.value.id), { headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {} })
    if (!resp.ok) throw new Error('导出失败')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `bank-${bank.value.id}.json`; a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '导出失败', 'error')
  } finally { exporting.value = false }
}

function statusVariant(s: string): 'default'|'success'|'warning'|'danger'|'info' {
  const m: Record<string, 'default'|'success'|'warning'|'danger'|'info'> = { none: 'default', pending: 'warning', processing: 'info', succeeded: 'success', failed: 'danger' }
  return m[s] || 'default'
}

onMounted(load)
</script>

<template>
  <section v-if="loading"><AppLoading /></section>

  <section v-else-if="bank" class="grid gap-5">
    <div class="page-card p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-xl font-bold">{{ bank.title }}</h1>
            <AppBadge :variant="bank.visibility === 'public' ? 'success' : 'default'">{{ bank.visibility === 'public' ? '公开' : '私有' }}</AppBadge>
            <AppBadge :variant="statusVariant(bank.generation_status)">{{ bank.generation_status }}</AppBadge>
          </div>
          <p class="mt-2 max-w-3xl text-slate-600">{{ bank.description || '暂无描述' }}</p>
          <div v-if="bank.tags.length" class="mt-2 flex flex-wrap gap-1.5">
            <span v-for="tag in bank.tags" :key="tag.id" class="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{{ tag.name }}</span>
          </div>
          <RouterLink class="mt-2 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-brand-600" :to="`/users/${bank.owner.id}`">
            <AppAvatar :src="bank.owner.avatar_url" :username="bank.owner.display_name || bank.owner.username" size="sm" />
            <span>{{ bank.owner.display_name || bank.owner.username }}</span>
          </RouterLink>
        </div>
        <AppButton variant="ghost" @click="favorite">{{ bank.is_favorited ? '取消收藏' : '收藏题库' }}</AppButton>
      </div>
      <div class="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">题目数</span><strong class="block text-slate-900">{{ bank.stats.question_count }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">收藏数</span><strong class="block text-slate-900">{{ bank.stats.favorite_count }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">生成状态</span><strong class="block text-slate-900">{{ bank.generation_status }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">模型</span><strong class="block text-slate-900">{{ bank.ai_model_name || '手动维护' }}</strong></div>
      </div>
    </div>

    <div class="page-card p-4">
      <h2 class="text-base font-semibold mb-2">练习与内容</h2>
      <div class="flex flex-wrap gap-2">
        <RouterLink v-if="bank.permissions.can_practice" :to="`/banks/${bank.id}/practice/setup`" class="inline-flex items-center rounded-btn bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">开始练习</RouterLink>
        <RouterLink v-if="bank.permissions.can_view_mistakes" :to="`/banks/${bank.id}/mistakes`" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">我的错题</RouterLink>
        <AppButton v-if="bank.permissions.can_export" variant="secondary" :loading="exporting" @click="exportJson">导出题库</AppButton>
        <RouterLink v-if="canManage" :to="`/banks/${bank.id}/questions`" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">题目管理</RouterLink>
        <RouterLink v-if="canManage" :to="`/banks/${bank.id}/generate`" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">扩展题库</RouterLink>
        <RouterLink
          v-if="canManage && bank.active_workflow && bank.active_workflow.status === 'draft_ready'"
          :to="`/ai-generation/workflows/${bank.active_workflow.id}/draft`"
          class="inline-flex items-center rounded-btn bg-amber-100 px-4 py-2 text-sm font-medium text-amber-800 hover:bg-amber-200"
        >确认草稿</RouterLink>
      </div>
    </div>

    <div v-if="canManage" class="page-card p-4">
      <h2 class="text-base font-semibold mb-2">题库管理</h2>
      <div class="flex flex-wrap gap-2">
        <AppButton variant="secondary" @click="editing = !editing">{{ editing ? '收起编辑' : '编辑题库' }}</AppButton>
        <AppButton variant="danger" @click="deleteModal = true">删除题库</AppButton>
      </div>
    </div>

    <div v-if="editing" class="page-card grid gap-2 p-4">
      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">题库名称</span>
        <input v-model="editForm.title" class="rounded-input border border-slate-300 bg-white px-3 py-2" />
      </label>
      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">描述</span>
        <textarea v-model="editForm.description" class="min-h-24 rounded-input border border-slate-300 bg-white px-3 py-2" />
      </label>
      <label class="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
        <input v-model="editIsPublic" type="checkbox" class="rounded" /> 公开题库
      </label>
      <BankTagInput v-model="editTags" allow-create label="标签" />
      <AppButton :loading="saving" @click="saveEdit">保存</AppButton>
    </div>

    <AppModal v-model="deleteModal" title="删除题库">
      <p class="text-slate-600">确定要删除「{{ bank.title }}」吗？题库和所有题目将被永久删除。</p>
      <template #footer>
        <AppButton variant="ghost" @click="deleteModal = false">取消</AppButton>
        <AppButton variant="danger" :loading="deleting" @click="removeBank">删除</AppButton>
      </template>
    </AppModal>
  </section>
</template>
