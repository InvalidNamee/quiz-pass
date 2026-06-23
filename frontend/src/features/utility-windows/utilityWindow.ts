import { WebviewWindow } from '@tauri-apps/api/webviewWindow'
import { isDesktopRuntime } from '../../local/db'

export type UtilityWindowKind =
  | 'local-practice-setup'
  | 'local-download'
  | 'bank-generate'
  | 'ai-config'
  | 'practice-setup'
  | 'workflow-retry'
  | 'bank-edit'
  | 'submit-practice'
  | 'tag-filter'
  | 'author-filter'
  | 'admin-user-edit'
  | 'admin-password-result'

export type UtilityWindowCompletedPayload = {
  kind: UtilityWindowKind
  requestId: string
  action: string
  result?: unknown
}

export type UtilityWindowCancelledPayload = {
  kind: UtilityWindowKind
  requestId: string
}

export function createUtilityRequestId(kind: string) {
  const random = Math.random().toString(36).slice(2, 10)
  return `${kind}_${Date.now()}_${random}`
}

function encodePayload(payload: Record<string, unknown>) {
  return encodeURIComponent(JSON.stringify(payload))
}

function safeWindowLabel(value: string) {
  return value.replace(/[^a-zA-Z0-9\-/:_]/g, '_').slice(0, 120)
}

export async function openUtilityWindow(
  kind: UtilityWindowKind,
  payload: Record<string, unknown>,
  options: { title: string; width: number; height: number; labelSeed?: string },
) {
  if (!isDesktopRuntime()) throw new Error('请在 Quiz Pass 桌面客户端中使用独立窗口')

  const requestId = String(payload.requestId || createUtilityRequestId(kind))
  const label = safeWindowLabel(`utility-${kind}-${options.labelSeed || requestId}`)
  const queryPayload = encodePayload({ ...payload, requestId })
  const url = `/index.html?utilityWindow=${encodeURIComponent(kind)}&payload=${queryPayload}`
  const existing = await WebviewWindow.getByLabel(label)
  if (existing) {
    await existing.setFocus().catch(() => undefined)
    return { requestId, window: existing }
  }

  const window = new WebviewWindow(label, {
    url,
    title: options.title,
    width: options.width,
    height: options.height,
    minWidth: options.width,
    minHeight: Math.min(options.height, 360),
    resizable: false,
    center: true,
  })

  window.once('tauri://error', (event) => {
    console.error(`创建 ${kind} 窗口失败`, event.payload)
  })

  return { requestId, window }
}

export function isUtilityWindowSupported() {
  return isDesktopRuntime()
}
