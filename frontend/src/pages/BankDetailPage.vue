<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type QuestionBank, type QuestionBankTag } from '../api/client'
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
const bank = ref<QuestionBank | null>(null)
const loading = ref(true)
const editing = ref(false)
const deleteModal = ref(false)
const editForm = ref({ title: '', description: '', visibility: 'private' })
const editTags = ref<QuestionBankTag[]>([])
const editIsPublic = computed({
  get: () => editForm.value.visibility === 'public',
  set: (val: boolean) => { editForm.value.visibility = val ? 'public' : 'private' },
})
const canManage = computed(() => Boolean(bank.value && auth.user && (auth.user.id === bank.value.owner_id || auth.user.role === 'admin')))
const saving = ref(false)
const deleting = ref(false)
const exporting = ref(false)

async function load() {
  loading.value = true
  try {
    bank.value = await api<QuestionBank>(`/api/v1/question-banks/${route.params.bankId}`)
    editForm.value = {
      title: bank.value.title,
      description: bank.value.description || '',
      visibility: bank.value.visibility,
    }
    editTags.value = bank.value.tags || []
  } finally {
    loading.value = false
  }
}

async function favorite() {
  if (!bank.value) return
  await api(`/api/v1/question-banks/${bank.value.id}/favorite`, { method: bank.value.is_favorited ? 'DELETE' : 'POST' })
  await load()
}

async function saveEdit() {
  if (!bank.value) return
  saving.value = true
  try {
    await api<QuestionBank>(`/api/v1/question-banks/${bank.value.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ ...editForm.value, tag_names: editTags.value.map(tag => tag.name) }),
    })
    editing.value = false
    toast.show('题库已更新', 'success')
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function removeBank() {
  if (!bank.value) return
  deleting.value = true
  try {
    await api(`/api/v1/question-banks/${bank.value.id}`, { method: 'DELETE' })
    deleteModal.value = false
    router.push('/banks')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

async function exportJson() {
  if (!bank.value) return
  exporting.value = true
  try {
    const response = await fetch(`/api/v1/question-banks/${bank.value.id}/export`, {
      headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
    })
    if (!response.ok) throw new Error('导出失败')
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `question-bank-${bank.value.id}.json`
    link.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '导出失败', 'error')
  } finally {
    exporting.value = false
  }
}

function statusVariant(status: string): 'default' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    none: 'default', pending: 'warning', processing: 'info', succeeded: 'success', failed: 'danger',
  }
  return map[status] || 'default'
}

onMounted(load)
</script>

<template>
  <section v-if="loading">
    <AppLoading />
  </section>

  <section v-else-if="bank" class="grid gap-5">
    <div class="page-card p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h1 class="text-2xl font-bold">{{ bank.title }}</h1>
            <AppBadge :variant="bank.visibility === 'public' ? 'success' : 'default'">{{ bank.visibility === 'public' ? '公开' : '私有' }}</AppBadge>
            <AppBadge :variant="statusVariant(bank.generation_status)">{{ bank.generation_status }}</AppBadge>
          </div>
          <p class="mt-3 max-w-3xl text-slate-600">{{ bank.description || '暂无描述' }}</p>
          <div v-if="bank.tags.length" class="mt-3 flex flex-wrap gap-1.5">
            <span v-for="tag in bank.tags" :key="tag.id" class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">{{ tag.name }}</span>
          </div>
          <RouterLink class="mt-4 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-brand-600" :to="`/users/${bank.owner_id}`">
            <AppAvatar :src="bank.owner_avatar_url" :username="bank.owner_display_name || bank.owner_username" size="sm" />
            <span>{{ bank.owner_display_name || bank.owner_username || `#${bank.owner_id}` }}</span>
          </RouterLink>
        </div>
        <AppButton variant="ghost" @click="favorite">{{ bank.is_favorited ? '取消收藏' : '收藏题库' }}</AppButton>
      </div>
      <div class="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">题目数</span><strong class="block text-slate-900">{{ bank.question_count }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">收藏数</span><strong class="block text-slate-900">{{ bank.favorite_count }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">生成状态</span><strong class="block text-slate-900">{{ bank.generation_status }}</strong></div>
        <div class="rounded-lg bg-slate-50 p-3"><span class="text-xs text-slate-500">模型</span><strong class="block text-slate-900">{{ bank.ai_model_name || '手动维护' }}</strong></div>
      </div>
    </div>

    <div class="page-card p-5">
      <h2 class="text-lg font-semibold mb-3">练习与内容</h2>
      <div class="flex flex-wrap gap-2">
        <RouterLink :to="`/banks/${bank.id}/practice/setup`" class="inline-flex items-center rounded-btn bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">开始练习</RouterLink>
        <RouterLink :to="`/banks/${bank.id}/mistakes`" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">我的错题</RouterLink>
        <AppButton variant="secondary" :loading="exporting" @click="exportJson">导出题库</AppButton>
        <RouterLink v-if="canManage" :to="`/banks/${bank.id}/questions`" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">题目管理</RouterLink>
        <RouterLink v-if="canManage" :to="`/banks/${bank.id}/import`" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-200">导入追加</RouterLink>
      </div>
    </div>

    <div v-if="canManage" class="page-card p-5">
      <h2 class="text-lg font-semibold mb-3">题库管理</h2>
      <div class="flex flex-wrap gap-2">
        <AppButton variant="secondary" @click="editing = !editing">{{ editing ? '收起编辑' : '编辑题库' }}</AppButton>
        <AppButton variant="danger" @click="deleteModal = true">删除题库</AppButton>
      </div>
    </div>

    <div v-if="editing" class="page-card grid gap-3 p-6">
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
