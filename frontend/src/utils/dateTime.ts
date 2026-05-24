const SHANGHAI_DATE_TIME_FORMATTER = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  hourCycle: 'h23',
})

function hasExplicitTimezone(value: string) {
  return /(?:z|[+-]\d{2}:?\d{2})$/i.test(value.trim())
}

function normalizeBackendDateTime(value: string) {
  const trimmed = value.trim()
  if (!trimmed) return trimmed
  if (/^\d{4}-\d{2}-\d{2}[T\s]/.test(trimmed) && !hasExplicitTimezone(trimmed)) {
    return `${trimmed.replace(' ', 'T')}Z`
  }
  return trimmed
}

export function formatDateTime(value: string | null | undefined, fallback = '-') {
  if (!value) return fallback
  const date = new Date(normalizeBackendDateTime(value))
  if (Number.isNaN(date.getTime())) return fallback

  const parts = SHANGHAI_DATE_TIME_FORMATTER.formatToParts(date)
  const map = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${map.year}-${map.month}-${map.day} ${map.hour}:${map.minute}`
}
