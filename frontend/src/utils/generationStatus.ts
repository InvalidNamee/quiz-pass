const UNSTABLE_BANK_STATUSES = new Set(['pending', 'processing'])
const UNSTABLE_WORKFLOW_STATUSES = new Set([
  'pending',
  'extracting',
  'extracting_document',
  'calling_model',
  'validating',
  'repairing',
])

export function isUnstableBankStatus(status: string | null | undefined) {
  return Boolean(status && UNSTABLE_BANK_STATUSES.has(status))
}

export function isUnstableWorkflowStatus(status: string | null | undefined) {
  return Boolean(status && UNSTABLE_WORKFLOW_STATUSES.has(status))
}

