<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authHeader, statusVariant } from '../api/http'
import { getBank, updateBank, updateBankAIContext, deleteBank, favoriteBank, unfavoriteBank, exportBankUrl, shareBank } from '../api/v2/banks'
import type { QuestionBankV2 } from '../api/types'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'
import UserAvatar from '../components/UserAvatar.vue'
import PracticeSetupDialog from '../components/PracticeSetupDialog.vue'
import GenerateBankDialog from '../components/GenerateBankDialog.vue'
import { isUnstableBankStatus, isUnstableWorkflowStatus } from '../utils/generationStatus'
import { Zap, Rocket, Download, Share2, FileText, Settings, Plus, CircleCheck, Star, Trash2 } from '@lucide/vue'
import { normalizeTagNames, tagKey, tagLabel, type TagInputValue } from '../features/tags/tagUtils'
import { ElMessageBox } from 'element-plus'

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

async function handleShare() {
  if (!bank.value) return
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
      const shared = await shareBank(bank.value!.id)
      toast.show(`已生成公开副本「${shared.title}」`, 'success')
      await load()
    } catch (err) {
      toast.show(err instanceof Error ? err.message : '分享失败', 'error')
    }
  }).catch(() => {})
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
  <section v-loading="loading" class="qp-page space-y-5" element-loading-text="加载中...">
    <template v-if="bank">
      <!-- Main Bank Info Card -->
      <div class="qp-section !p-6 shadow-sm border border-slate-100/80">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-2">
              <button
                class="text-2xl leading-none transition-transform hover:scale-125 duration-150 active:scale-95"
                :class="bank.is_favorited ? 'text-amber-500' : 'text-slate-300 hover:text-amber-400'"
                @click="favorite"
              >
                <Star :size="24" :fill="bank.is_favorited ? '#f59e0b' : 'none'" :stroke="bank.is_favorited ? '#f59e0b' : '#94a3b8'" />
              </button>
              <h1 class="text-xl font-extrabold text-slate-800 tracking-tight">{{ bank.title }}</h1>

              <el-tag size="small" class="!rounded-md" :type="bank.visibility === 'public' ? 'success' : 'info'">
                {{ bank.visibility === 'public' ? '公开' : '私有' }}
              </el-tag>
              <el-tag v-if="bank.is_shared_copy" size="small" class="!rounded-md" type="info">共享副本</el-tag>
              <el-tag size="small" class="!rounded-md" :type="statusVariant(bank.generation_status)">{{ bank.generation_status }}</el-tag>
            </div>

            <p class="mt-2.5 max-w-3xl text-sm text-slate-500 leading-relaxed">{{ bank.description || '暂无描述' }}</p>

            <div v-if="bank.tags.length" class="mt-3 flex flex-wrap gap-1.5">
              <el-tag v-for="tag in bank.tags" :key="tag.id" size="small" type="info" class="!rounded-md !bg-slate-50 !border-slate-100 !text-slate-500">{{ tag.name }}</el-tag>
            </div>

            <div class="mt-4 flex items-center">
              <RouterLink class="inline-flex items-center gap-2.5 text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors" :to="`/users/${bank.owner.id}`">
                <UserAvatar :src="bank.owner.avatar_url" :name="bank.owner.display_name || bank.owner.username" :size="26" class="ring-2 ring-indigo-500/10 shadow-sm" />
                <span>{{ bank.owner.display_name || bank.owner.username }}</span>
              </RouterLink>
            </div>
          </div>
        </div>

        <el-descriptions :column="4" border class="mt-5 !rounded-xl overflow-hidden border-slate-100" size="small">
          <el-descriptions-item label="题目数量"><span class="font-bold text-slate-800">{{ bank.stats.question_count }} 题</span></el-descriptions-item>
          <el-descriptions-item label="收藏人数"><span class="text-slate-600">{{ bank.stats.favorite_count }} 次</span></el-descriptions-item>
          <el-descriptions-item label="生成状态"><span class="text-slate-600">{{ bank.generation_status }}</span></el-descriptions-item>
          <el-descriptions-item label="AI 命题模型"><span class="text-slate-600 font-mono">{{ bank.ai_model_name || '手动维护' }}</span></el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- Practice and Actions Card -->
      <div class="qp-section space-y-3.5 shadow-sm border border-slate-100/80">
        <h2 class="qp-section-title !mb-0 flex items-center gap-1.5 text-slate-800">
          <span>练习与内容</span>
        </h2>
        <div class="flex flex-wrap gap-2 pt-1">
          <el-button
            v-if="bank.resumable_session"
            type="primary"
            class="!rounded-xl !bg-gradient-to-r !from-indigo-500 !to-indigo-600 !border-none shadow-md shadow-indigo-500/10 active:scale-95 transition-all"
            @click="continuePractice"
          >
            <Zap :size="14" class="mr-1" />继续练习
          </el-button>

          <el-button
            v-if="bank.permissions.can_practice"
            class="!rounded-xl active:scale-95 transition-all"
            @click="practiceDialogVisible = true"
          >
            <Rocket :size="14" class="mr-1" />开始练习
          </el-button>

          <RouterLink v-if="bank.permissions.can_view_mistakes" :to="`/banks/${bank.id}/mistakes`">
            <el-button class="!rounded-xl active:scale-95 transition-all"><CircleX :size="14" class="mr-1" />我的错题</el-button>
          </RouterLink>

          <el-button v-if="bank.permissions.can_export" :loading="exporting" class="!rounded-xl active:scale-95 transition-all" @click="exportJson"><Download :size="14" class="mr-1" />导出 JSON</el-button>
          <el-button v-if="bank.permissions.can_share" class="!rounded-xl active:scale-95 transition-all" @click="handleShare"><Share2 :size="14" class="mr-1" />共享题库</el-button>

          <RouterLink :to="`/banks/${bank.id}/workflows`">
            <el-button class="!rounded-xl active:scale-95 transition-all"><FileText :size="14" class="mr-1" />生成日志</el-button>
          </RouterLink>

          <RouterLink v-if="canManage" :to="`/banks/${bank.id}/questions`">
            <el-button class="!rounded-xl active:scale-95 transition-all"><Settings :size="14" class="mr-1" />题目管理</el-button>
          </RouterLink>

          <el-button v-if="canManage" class="!rounded-xl active:scale-95 transition-all" @click="generateDialogVisible = true"><Plus :size="14" class="mr-1" />扩展题目</el-button>

          <RouterLink
            v-if="canManage && bank.active_workflow && bank.active_workflow.status === 'draft_ready'"
            :to="`/ai-generation/workflows/${bank.active_workflow.id}/draft`"
          >
            <el-button type="warning" class="!rounded-xl shadow-md shadow-amber-500/10 active:scale-95 transition-all"><CircleCheck :size="14" class="mr-1" />确认草稿</el-button>
          </RouterLink>
        </div>
      </div>

      <!-- Bank Management Panel Card -->
      <div v-if="canManage" class="qp-section space-y-3.5 shadow-sm border border-slate-100/80">
        <h2 class="qp-section-title !mb-0 text-slate-800">题库管理</h2>
        <div class="flex flex-wrap gap-2 pt-1">
          <el-button class="!rounded-xl active:scale-95 transition-all" @click="editing = !editing">
            ✏️ {{ editing ? '收起编辑' : '编辑基本信息' }}
          </el-button>
          <el-button type="danger" plain class="!rounded-xl active:scale-95 transition-all" @click="deleteModal = true"><Trash2 :size="14" class="mr-1" />删除题库</el-button>
        </div>
      </div>

      <!-- AI Background Prompt Context -->
      <div v-if="canManage" class="qp-section space-y-3.5 shadow-sm border border-slate-100/80">
        <div class="flex items-center justify-between gap-2">
          <h2 class="qp-section-title !mb-0 text-slate-800">🤖 AI 命题背景知识</h2>
          <el-button
            size="small"
            type="primary"
            class="!rounded-lg !px-4 shadow-sm active:scale-95 transition-all"
            :loading="savingAIContext"
            @click="saveAIContext"
          >
            保存配置
          </el-button>
        </div>
        <p class="text-xs text-slate-400 mt-1">此配置将被该题库后续 AI 扩展所继承，用于约束命题风格、覆盖范围或防止生成重复题目。</p>
        <el-input
          v-model="aiContext"
          type="textarea"
          :rows="4"
          maxlength="12000"
          show-word-limit
          class="mt-2"
          placeholder="例如：1. 聚焦实战场景，避免空洞概念；2. 命题风格偏向严谨；3. 避免生成与已有知识库高度重复的题目..."
        />
      </div>

      <!-- Edit Form Section (Dynamic) -->
      <el-form v-if="editing" class="qp-section space-y-4 shadow-lg border border-slate-150" label-position="top">
        <h3 class="text-sm font-bold text-slate-700 pb-2 border-b border-slate-100">修改题库信息</h3>
        <el-form-item label="题库名称"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="题库描述"><el-input v-model="editForm.description" type="textarea" :rows="4" /></el-form-item>
        <el-form-item v-if="auth.user?.role === 'admin'"><el-checkbox v-model="editIsPublic">公开此题库</el-checkbox></el-form-item>
        <el-form-item label="题库标签">
          <div class="flex flex-wrap gap-1.5 mb-2.5">
            <el-tag v-for="(tag, i) in editTags" :key="tagKey(tag, i)" closable size="small" :disable-transitions="true" class="!rounded-md" @close="editTags.splice(i, 1)">{{ tagLabel(tag) }}</el-tag>
          </div>
          <el-select v-model="editTags" multiple filterable allow-create default-first-option clearable placeholder="添加或创建标签" style="width: 100%">
            <el-option v-for="(tag, i) in editTags" :key="tagKey(tag, i)" :label="tagLabel(tag)" :value="tag" />
          </el-select>
        </el-form-item>
        <div class="pt-2">
          <el-button
            type="primary"
            class="!rounded-xl shadow-md shadow-indigo-500/10 active:scale-95 transition-all"
            :loading="saving"
            @click="saveEdit"
          >
            保存修改
          </el-button>
        </div>
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
