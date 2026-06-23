import type { AIProviderConfig, QuestionBankTag, QuestionBankV2, UserMe, UserPublic } from '../../api/types'
import { openUtilityWindow } from './utilityWindow'

export function openBankGenerateWindow(payload: { extendBankId?: number | null; title?: string } = {}) {
  return openUtilityWindow(
    'bank-generate',
    { extendBankId: payload.extendBankId || null },
    {
      title: payload.extendBankId ? '扩展题库' : '新建题库',
      width: 800,
      height: 780,
      labelSeed: payload.extendBankId ? `extend-${payload.extendBankId}` : 'create',
    },
  )
}

export function openAIConfigWindow(payload: {
  configId?: number | null
  initialConfig?: Pick<AIProviderConfig, 'name' | 'api_base_url' | 'model' | 'response_format_type' | 'is_default'> | null
} = {}) {
  return openUtilityWindow(
    'ai-config',
    { configId: payload.configId || null, initialConfig: payload.initialConfig || null },
    {
      title: payload.configId ? '编辑 AI 配置' : '添加 AI 配置',
      width: 500,
      height: 610,
      labelSeed: payload.configId ? `edit-${payload.configId}` : 'add',
    },
  )
}

export function openPracticeSetupWindow(payload: { bank: QuestionBankV2 }) {
  return openUtilityWindow(
    'practice-setup',
    { bankId: payload.bank.id, title: payload.bank.title },
    {
      title: '开始练习',
      width: 560,
      height: 610,
      labelSeed: `bank-${payload.bank.id}`,
    },
  )
}

export function openBankEditWindow(payload: { bankId: number; title?: string }) {
  return openUtilityWindow(
    'bank-edit',
    { bankId: payload.bankId },
    {
      title: '编辑基本信息',
      width: 640,
      height: 620,
      labelSeed: `bank-${payload.bankId}`,
    },
  )
}

export function openWorkflowRetryWindow(payload: { workflowId: number }) {
  return openUtilityWindow(
    'workflow-retry',
    { workflowId: payload.workflowId },
    {
      title: '重新生成',
      width: 800,
      height: 780,
      labelSeed: `workflow-${payload.workflowId}`,
    },
  )
}

export function openSubmitPracticeWindow(payload: { local?: boolean; sessionId: number }) {
  return openUtilityWindow(
    'submit-practice',
    { local: Boolean(payload.local), sessionId: payload.sessionId },
    {
      title: payload.local ? '提交本地练习' : '提交试卷',
      width: 460,
      height: 360,
      labelSeed: `${payload.local ? 'local' : 'online'}-${payload.sessionId}`,
    },
  )
}

export function openTagFilterWindow(payload: { selectedTags: QuestionBankTag[] }) {
  return openUtilityWindow(
    'tag-filter',
    { selectedTags: payload.selectedTags },
    {
      title: '选择标签',
      width: 460,
      height: 520,
      labelSeed: 'tag-filter',
    },
  )
}

export function openAuthorFilterWindow(payload: { selectedUser: UserPublic | null }) {
  return openUtilityWindow(
    'author-filter',
    { selectedUser: payload.selectedUser },
    {
      title: '选择作者',
      width: 460,
      height: 520,
      labelSeed: 'author-filter',
    },
  )
}

export function openAdminUserEditWindow(payload: { user: UserMe }) {
  return openUtilityWindow(
    'admin-user-edit',
    { user: payload.user },
    {
      title: '编辑用户',
      width: 520,
      height: 520,
      labelSeed: `user-${payload.user.id}`,
    },
  )
}

export function openAdminPasswordResultWindow(payload: { userId: number; temporaryPassword: string }) {
  return openUtilityWindow(
    'admin-password-result',
    { userId: payload.userId, temporaryPassword: payload.temporaryPassword },
    {
      title: '临时密码',
      width: 500,
      height: 280,
      labelSeed: `password-${payload.userId}`,
    },
  )
}
