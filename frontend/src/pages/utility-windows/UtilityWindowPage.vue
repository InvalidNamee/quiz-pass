<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { emit } from '@tauri-apps/api/event'
import { getCurrentWindow } from '@tauri-apps/api/window'
import GenerateBankDialog from '../../components/GenerateBankDialog.vue'
import AIConfigDialog from '../../components/AIConfigDialog.vue'
import PracticeSetupDialog from '../../components/PracticeSetupDialog.vue'
import LocalDownloadWindow from '../local-windows/LocalDownloadWindow.vue'
import LocalPracticeSetupWindow from '../local-windows/LocalPracticeSetupWindow.vue'
import BankEditWindow from './BankEditWindow.vue'
import SubmitPracticeWindow from './SubmitPracticeWindow.vue'
import WorkflowRetryWindow from './WorkflowRetryWindow.vue'
import TagFilterWindow from './TagFilterWindow.vue'
import AuthorFilterWindow from './AuthorFilterWindow.vue'
import AdminUserEditWindow from './AdminUserEditWindow.vue'
import AdminPasswordResultWindow from './AdminPasswordResultWindow.vue'
import type { UtilityWindowCompletedPayload, UtilityWindowKind } from '../../features/utility-windows/utilityWindow'

type UtilityPayload = Record<string, unknown> & {
  requestId?: string
  bankId?: number
  extendBankId?: number
  configId?: number
  initialConfig?: {
    name: string
    api_base_url: string
    model: string
    response_format_type: 'json_object' | 'json_schema'
    is_default: boolean
  }
}

const route = useRoute()
const dialogVisible = ref(true)

const kind = computed(() => {
  if (route.query.utilityWindow) return String(route.query.utilityWindow) as UtilityWindowKind
  if (route.query.localWindow === 'practice-setup') return 'local-practice-setup'
  if (route.query.localWindow === 'download') return 'local-download'
  return '' as UtilityWindowKind
})
const payload = computed<UtilityPayload>(() => {
  const raw = route.query.payload
  if (typeof raw === 'string' && raw.trim()) {
    try {
      return JSON.parse(decodeURIComponent(raw)) as UtilityPayload
    } catch {
      return {}
    }
  }
  // Compatibility for earlier local prototype query strings.
  return {
    requestId: 'legacy',
    localBankId: route.query.localBankId ? Number(route.query.localBankId) : undefined,
    remoteBankId: route.query.remoteBankId ? Number(route.query.remoteBankId) : undefined,
    title: route.query.title,
    alreadyDownloaded: route.query.alreadyDownloaded === 'true',
  }
})

const requestId = computed(() => String(payload.value.requestId || 'utility-window'))

async function complete(action: string, result?: unknown) {
  const event: UtilityWindowCompletedPayload = { kind: kind.value, requestId: requestId.value, action, result }
  await emit('utility-window-completed', event)
  await getCurrentWindow().close()
}

function closeWindow() {
  getCurrentWindow().close().catch(() => undefined)
}
</script>

<template>
  <section class="min-h-screen bg-white">
    <GenerateBankDialog
      v-if="kind === 'bank-generate'"
      v-model="dialogVisible"
      :extend-bank-id="typeof payload.extendBankId === 'number' ? payload.extendBankId : null"
      :navigate-on-submit="false"
      @submitted="complete('bank-generate-submitted')"
      @update:model-value="(value: boolean) => { if (!value) closeWindow() }"
    />

    <AIConfigDialog
      v-else-if="kind === 'ai-config'"
      v-model="dialogVisible"
      :config-id="typeof payload.configId === 'number' ? payload.configId : null"
      :initial-config="payload.initialConfig || null"
      @submitted="complete('ai-config-saved')"
      @update:model-value="(value: boolean) => { if (!value) closeWindow() }"
    />

    <PracticeSetupDialog
      v-else-if="kind === 'practice-setup'"
      v-model="dialogVisible"
      :bank-id="typeof payload.bankId === 'number' ? payload.bankId : null"
      :navigate-on-start="false"
      @started="(sessionId: number) => complete('practice-created', { sessionId, bankId: payload.bankId })"
      @update:model-value="(value: boolean) => { if (!value) closeWindow() }"
    />

    <LocalPracticeSetupWindow v-else-if="kind === 'local-practice-setup'" />
    <LocalDownloadWindow v-else-if="kind === 'local-download'" />
    <BankEditWindow v-else-if="kind === 'bank-edit'" />
    <SubmitPracticeWindow v-else-if="kind === 'submit-practice'" />
    <WorkflowRetryWindow v-else-if="kind === 'workflow-retry'" />
    <TagFilterWindow v-else-if="kind === 'tag-filter'" />
    <AuthorFilterWindow v-else-if="kind === 'author-filter'" />
    <AdminUserEditWindow v-else-if="kind === 'admin-user-edit'" />
    <AdminPasswordResultWindow v-else-if="kind === 'admin-password-result'" />

    <div v-else class="p-4 text-sm text-slate-500">
      未知的独立窗口类型：{{ kind || '空' }}
    </div>
  </section>
</template>
