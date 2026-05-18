import { api } from './http'
import type { Page, UserMe, UserPublic, QuestionBank, AIProviderConfig } from './types'

export function updateProfile(data: Record<string, unknown>) {
  return api<UserMe>('/api/v1/users/me', { method: 'PATCH', body: JSON.stringify(data) })
}

export function changePassword(oldPassword: string, newPassword: string) {
  return api('/api/v1/users/me/change-password', {
    method: 'POST',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  })
}

export function searchUsers(params: { page?: number; keyword?: string }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  return api<Page<UserPublic>>(`/api/v1/users/search?${q}`)
}

export function getUserPublic(userId: number) {
  return api<UserPublic>(`/api/v1/users/${userId}`)
}

export function getUserPublicBanks(userId: number) {
  return api<QuestionBank[]>(`/api/v1/users/${userId}/public-question-banks`)
}

export function listAIConfigs() {
  return api<AIProviderConfig[]>('/api/v1/users/me/ai-provider-configs')
}

export function createAIConfig(data: { name: string; api_base_url: string; api_key: string; model: string; is_default: boolean }) {
  return api<AIProviderConfig>('/api/v1/users/me/ai-provider-configs', { method: 'POST', body: JSON.stringify(data) })
}

export function updateAIConfig(configId: number, data: Record<string, unknown>) {
  return api<AIProviderConfig>(`/api/v1/users/me/ai-provider-configs/${configId}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function setDefaultAIConfig(configId: number) {
  return api(`/api/v1/users/me/ai-provider-configs/${configId}/set-default`, { method: 'POST' })
}

export function testAIConfig(configId: number) {
  return api(`/api/v1/users/me/ai-provider-configs/${configId}/test`, { method: 'POST' })
}

export function deleteAIConfig(configId: number) {
  return api(`/api/v1/users/me/ai-provider-configs/${configId}`, { method: 'DELETE' })
}

export function listAdminUsers(params: { page?: number; keyword?: string; role?: string; is_active?: string }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<UserMe>>(`/api/v1/admin/users?${q}`)
}
