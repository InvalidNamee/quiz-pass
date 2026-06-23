<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { isDesktopRuntime } from '../../local/db'
import type { UtilityWindowCancelledPayload, UtilityWindowCompletedPayload } from './utilityWindow'

const router = useRouter()
const unlisteners: UnlistenFn[] = []

function dispatchCompleted(payload: UtilityWindowCompletedPayload) {
  window.dispatchEvent(new CustomEvent('quiz-pass:utility-window-completed', { detail: payload }))

  if (payload.action === 'practice-created') {
    const result = payload.result as { sessionId?: number; localSessionId?: number } | undefined
    if (result?.sessionId) router.push(`/practice/session/${result.sessionId}`)
    if (result?.localSessionId) router.push(`/local/practice/session/${result.localSessionId}`)
  }

  if (payload.action === 'local-bank-downloaded') {
    window.dispatchEvent(new CustomEvent('quiz-pass:local-bank-downloaded', { detail: payload.result }))
  }
}

onMounted(async () => {
  if (!isDesktopRuntime()) return

  unlisteners.push(await listen<UtilityWindowCompletedPayload>('utility-window-completed', (event) => {
    dispatchCompleted(event.payload)
  }))

  unlisteners.push(await listen<UtilityWindowCancelledPayload>('utility-window-cancelled', (event) => {
    window.dispatchEvent(new CustomEvent('quiz-pass:utility-window-cancelled', { detail: event.payload }))
  }))

  // Backward-compatible listeners for the first local window prototype.
  unlisteners.push(await listen<{ sessionId: number; localBankId: number }>('local-practice-created', (event) => {
    dispatchCompleted({
      kind: 'local-practice-setup',
      requestId: 'legacy-local-practice',
      action: 'practice-created',
      result: { localSessionId: event.payload.sessionId, localBankId: event.payload.localBankId },
    })
  }))

  unlisteners.push(await listen<{ remoteBankId: number; localBankId: number; downloadedAt: string }>('local-bank-downloaded', (event) => {
    dispatchCompleted({
      kind: 'local-download',
      requestId: 'legacy-local-download',
      action: 'local-bank-downloaded',
      result: event.payload,
    })
  }))
})

onBeforeUnmount(() => {
  while (unlisteners.length) unlisteners.pop()?.()
})
</script>

<template>
  <span hidden />
</template>
