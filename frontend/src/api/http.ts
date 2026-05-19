const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    if (typeof error?.error?.message === 'string' && error.error.message) {
      throw new Error(error.error.message)
    }
    if (typeof error?.detail === 'string') throw new Error(error.detail)
    if (Array.isArray(error?.detail)) {
      const message = error.detail
        .map((item: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : ''
          return field ? `${field}: ${item.msg ?? '校验失败'}` : item.msg ?? '校验失败'
        })
        .join('；')
      throw new Error(message || '请求参数校验失败')
    }
    throw new Error('请求失败')
  }
  return response.json()
}

export function buildQuery(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== '') q.set(k, String(v))
  })
  return q.toString()
}

export function authHeader(): Record<string, string> {
  const token = localStorage.getItem('access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function statusVariant(status: string): 'default' | 'success' | 'warning' | 'danger' | 'info' {
  const m: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    none: 'default', pending: 'warning', processing: 'info', succeeded: 'success', failed: 'danger',
  }
  return m[status] || 'default'
}
