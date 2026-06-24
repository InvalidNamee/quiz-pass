<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import LocalDownloadWindow from '../local-windows/LocalDownloadWindow.vue'
import LocalPracticeSetupWindow from '../local-windows/LocalPracticeSetupWindow.vue'
import AIConfigWindow from './AIConfigWindow.vue'
import AdminPasswordResultWindow from './AdminPasswordResultWindow.vue'
import AdminUserEditWindow from './AdminUserEditWindow.vue'
import AuthorFilterWindow from './AuthorFilterWindow.vue'
import BankEditWindow from './BankEditWindow.vue'
import BankGenerateWindow from './BankGenerateWindow.vue'
import PracticeSetupWindow from './PracticeSetupWindow.vue'
import SubmitPracticeWindow from './SubmitPracticeWindow.vue'
import TagFilterWindow from './TagFilterWindow.vue'
import WorkflowRetryWindow from './WorkflowRetryWindow.vue'
import type { UtilityWindowKind } from '../../features/utility-windows/utilityWindow'

const route = useRoute()

const kind = computed(() => {
  if (route.query.utilityWindow) return String(route.query.utilityWindow) as UtilityWindowKind
  if (route.query.localWindow === 'practice-setup') return 'local-practice-setup'
  if (route.query.localWindow === 'download') return 'local-download'
  return '' as UtilityWindowKind
})
</script>

<template>
  <section class="min-h-screen bg-white">
    <BankGenerateWindow v-if="kind === 'bank-generate'" />
    <AIConfigWindow v-else-if="kind === 'ai-config'" />
    <PracticeSetupWindow v-else-if="kind === 'practice-setup'" />
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
