<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authHeader, statusVariant } from '../api/http'
import { getBank, updateBank, updateBankAIContext, deleteBank, favoriteBank, unfavoriteBank, exportBankUrl } from '../api/v2/banks'
import type { QuestionBankV2 } from '../api/types'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'
import UserAvatar from '../components/UserAvatar.vue'
import PracticeSetupDialog from '../components/PracticeSetupDialog.vue'
import GenerateBankDialog from '../components/GenerateBankDialog.vue'
import { isUnstableBankStatus, isUnstableWorkflowStatus } from '../utils/generationStatus'
import { normalizeTagNames, tagKey, tagLabel, type TagInputValue } from '../features/tags/tagUtils'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const bank = ref<QuestionBankV2 | null>(null)
const loading = ref(true)
const editing = ref(false)
const deleteModal = ref(false)
const editForm = ref({ title: '', description: '', visibility: 'private' })
const editTags = ref<TagInputValue[]>([])
const editIsPublic = computed({
  get: () => editForm.value.visibility === 'public',
  set: (val: boolean) => { editForm.value.visibility = val ? 'public' : 'private' },
})
const canManage = computed(() => bank.value?.permissions.can_manage ?? false)
const saving = ref(false)
const deleting = ref(false)
const exporting = ref(false)
const practiceDialogVisible = ref(false)
const generateDialogVisible = ref(false)
const aiContext = ref('')
const savingAIContext = ref(false)
let pollingTimer: number | null = null

function shouldPollBank() {
  return isUnstableBankStatus(bank.value?.generation_status) || isUnstableWorkflowStatus(bank.value?.active_workflow?.status)
}

function stopPolling() {
  if (pollingTimer !== null) {
    window.clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function syncPolling() {
  if (!shouldPollBank()) {
    stopPolling()
    return
  }
  if (pollingTimer === null) {
    pollingTimer = window.setInterval(() => {
      if (shouldPollBank()) void load(true)
      else stopPolling()
    }, 3000)
  }
}

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    bank.value = await getBank(Number(route.params.bankId))
    editForm.value = {
      title: bank.value.title,
      description: bank.value.description || '',
      visibility: bank.value.visibility,
    }
    editTags.value = bank.value.tags || []
    aiContext.value = bank.value.ai_context || ''
  } finally { if (!silent) loading.value = false }
}

async function favorite() {
  if (!bank.value) return
  try {
    if (bank.value.is_favorited) { await unfavoriteBank(bank.value.id); toast.show('已取消收藏', 'success') }
    else { await favoriteBank(bank.value.id); toast.show('已收藏', 'success') }
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '操作失败', 'error')
  }
}

async function saveEdit() {
  if (!bank.value) return
  saving.value = true
  try {
    await updateBank(bank.value.id, { ...editForm.value, tag_names: normalizeTagNames(editTags.value) })
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
    toast.show('题库已删除', 'success')
    router.push('/banks')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '删除失败', 'error')
  } finally { deleting.value = false }
}

async function exportJson() {
  if (!bank.value) return
  exporting.value = true
  try {
    const resp = await fetch(exportBankUrl(bank.value.id), { headers: authHeader() })
    if (!resp.ok) throw new Error('导出失败')
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = `bank-${bank.value.id}.json`; a.click()
    URL.revokeObjectURL(url)
    toast.show('导出成功', 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '导出失败', 'error')
  } finally { exporting.value = false }
}

async function saveAIContext() {
  if (!bank.value) return
  savingAIContext.value = true
  try {
    bank.value = await updateBankAIContext(bank.value.id, aiContext.value.trim() || null)
    aiContext.value = bank.value.ai_context || ''
    toast.show('AI 上下文已保存', 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    savingAIContext.value = false
  }
}

function continuePractice() {
  if (!bank.value?.resumable_session) return
  router.push(`/practice/session/${bank.value.resumable_session.id}`)
}

onMounted(load)
watch(bank, syncPolling, { deep: true })
onBeforeUnmount(stopPolling)
</script>

<template>
  <section v-loading="loading" class="qp-page" element-loading-text="加载中...">
    <template v-if="bank">
      <div class="qp-section">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h1 class="text-lg font-semibold text-slate-900">{{ bank.title }}</h1>
              <el-tag :type="bank.visibility === 'public' ? 'success' : 'info'">{{ bank.visibility === 'public' ? '公开' : '私有' }}</el-tag>
              <el-tag :type="statusVariant(bank.generation_status)">{{ bank.generation_status }}</el-tag>
            </div>
            <p class="mt-2 max-w-3xl text-sm text-slate-600">{{ bank.description || '暂无描述' }}</p>
            <div v-if="bank.tags.length" class="mt-2 flex flex-wrap gap-1.5">
              <el-tag v-for="tag in bank.tags" :key="tag.id" size="small" type="info">{{ tag.name }}</el-tag>
            </div>
            <RouterLink class="mt-2 inline-flex items-center gap-2 text-sm text-slate-600 hover:text-brand-600" :to="`/users/${bank.owner.id}`">
              <UserAvatar :src="bank.owner.avatar_url" :name="bank.owner.display_name || bank.owner.username" :size="30" />
              <span>{{ bank.owner.display_name || bank.owner.username }}</span>
            </RouterLink>
          </div>
          <el-button text @click="favorite">{{ bank.is_favorited ? '取消收藏' : '收藏题库' }}</el-button>
        </div>
        <el-descriptions :column="4" border class="mt-3" size="small">
          <el-descriptions-item label="题目数">{{ bank.stats.question_count }}</el-descriptions-item>
          <el-descriptions-item label="收藏数">{{ bank.stats.favorite_count }}</el-descriptions-item>
          <el-descriptions-item label="生成状态">{{ bank.generation_status }}</el-descriptions-item>
          <el-descriptions-item label="模型">{{ bank.ai_model_name || '手动维护' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="qp-section">
        <h2 class="qp-section-title">练习与内容</h2>
        <div class="flex flex-wrap gap-2">
          <el-button v-if="bank.resumable_session" type="primary" plain @click="continuePractice">继续练习</el-button>
          <el-button v-if="bank.permissions.can_practice" type="primary" @click="practiceDialogVisible = true">开始练习</el-button>
          <RouterLink v-if="bank.permissions.can_view_mistakes" :to="`/banks/${bank.id}/mistakes`"><el-button>我的错题</el-button></RouterLink>
          <el-button v-if="bank.permissions.can_export" :loading="exporting" @click="exportJson">导出题库</el-button>
          <RouterLink :to="`/banks/${bank.id}/workflows`"><el-button>生成日志</el-button></RouterLink>
          <RouterLink v-if="canManage" :to="`/banks/${bank.id}/questions`"><el-button>题目管理</el-button></RouterLink>
          <el-button v-if="canManage" @click="generateDialogVisible = true">扩展题库</el-button>
          <RouterLink
            v-if="canManage && bank.active_workflow && bank.active_workflow.status === 'draft_ready'"
            :to="`/ai-generation/workflows/${bank.active_workflow.id}/draft`"
          ><el-button type="warning">确认草稿</el-button></RouterLink>
        </div>
      </div>

      <div v-if="canManage" class="qp-section">
        <h2 class="qp-section-title">题库管理</h2>
        <div class="flex flex-wrap gap-2">
          <el-button @click="editing = !editing">{{ editing ? '收起编辑' : '编辑题库' }}</el-button>
          <el-button type="danger" @click="deleteModal = true">删除题库</el-button>
        </div>
      </div>

      <div v-if="canManage" class="qp-section">
        <div class="mb-2 flex items-center justify-between gap-2">
          <h2 class="qp-section-title m-0">AI 背景</h2>
          <el-button size="small" type="primary" :loading="savingAIContext" @click="saveAIContext">保存</el-button>
        </div>
        <el-input
          v-model="aiContext"
          type="textarea"
          :rows="4"
          maxlength="12000"
          show-word-limit
          placeholder="写给后续扩展题库继承的背景、命题风格、覆盖范围或避免重复的规则"
        />
      </div>

      <el-form v-if="editing" class="qp-section" label-position="top">
        <el-form-item label="题库名称"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="editForm.description" type="textarea" :rows="4" /></el-form-item>
        <el-form-item><el-checkbox v-model="editIsPublic">公开题库</el-checkbox></el-form-item>
        <el-form-item label="标签">
          <div class="flex flex-wrap gap-1.5 mb-2">
            <el-tag v-for="(tag, i) in editTags" :key="tagKey(tag, i)" closable size="small" :disable-transitions="true" @close="editTags.splice(i, 1)">{{ tagLabel(tag) }}</el-tag>
          </div>
          <el-select v-model="editTags" multiple filterable allow-create default-first-option clearable placeholder="添加标签" style="width: 100%">
            <el-option v-for="(tag, i) in editTags" :key="tagKey(tag, i)" :label="tagLabel(tag)" :value="tag" />
          </el-select>
        </el-form-item>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </el-form>

      <el-dialog v-model="deleteModal" title="删除题库" width="400px">
        <p>确定要删除「{{ bank.title }}」吗？题库和所有题目将被永久删除。</p>
        <template #footer>
          <el-button @click="deleteModal = false">取消</el-button>
          <el-button type="danger" :loading="deleting" @click="removeBank">删除</el-button>
        </template>
      </el-dialog>

      <PracticeSetupDialog v-model="practiceDialogVisible" :bank-id="bank.id" :initial-bank="bank" />
      <GenerateBankDialog v-model="generateDialogVisible" :extend-bank-id="bank.id" :initial-bank="bank" />
    </template>
  </section>
</template>
