export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

type TokenResponse = {
  access_token: string
  refresh_token: string
  token_type: string
}

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/api/v2/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error('refresh failed')
        const data = await response.json() as TokenResponse
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        return data.access_token
      })
      .catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  return requestWithAuth<T>(path, options, true)
}

async function requestWithAuth<T>(path: string, options: RequestInit = {}, allowRefresh: boolean): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 401 && allowRefresh && !path.includes('/auth/refresh')) {
    const nextToken = await refreshAccessToken()
    if (nextToken) {
      return requestWithAuth<T>(path, options, false)
    }
  }
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
