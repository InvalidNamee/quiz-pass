import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { emit } from '@tauri-apps/api/event'
import { getCurrentWindow } from '@tauri-apps/api/window'
import type { UtilityWindowCompletedPayload, UtilityWindowKind } from './utilityWindow'

export function useUtilityWindowPage<TPayload extends Record<string, unknown> = Record<string, unknown>>(
  fallbackKind: UtilityWindowKind,
) {
  const route = useRoute()
  const payload = computed<TPayload>(() => {
    const raw = route.query.payload
    if (typeof raw !== 'string' || !raw.trim()) return {} as TPayload
    try {
      return JSON.parse(decodeURIComponent(raw)) as TPayload
    } catch {
      return {} as TPayload
    }
  })
  const requestId = computed(() => String((payload.value as Record<string, unknown>).requestId || 'utility-window'))
  const kind = computed(() => String(route.query.utilityWindow || fallbackKind) as UtilityWindowKind)

  async function complete(action: string, result?: unknown) {
    const event: UtilityWindowCompletedPayload = { kind: kind.value, requestId: requestId.value, action, result }
    await emit('utility-window-completed', event)
    await getCurrentWindow().close()
  }

  function closeWindow() {
    getCurrentWindow().close().catch(() => undefined)
  }

  return { payload, requestId, kind, complete, closeWindow }
}
