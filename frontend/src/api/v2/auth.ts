import { api } from '../http'
import type { UserMe } from '../types'

type TokenResponse = { access_token: string; refresh_token: string; token_type: string }
export type AuthMessage = { ok: boolean; message: string; debug_token?: string | null }

export function login(identifier: string, password: string) {
  return api<TokenResponse>('/api/v2/auth/login', {
    method: 'POST',
    body: JSON.stringify({ identifier, password }),
  })
}

export function register(email: string, username: string, password: string) {
  return api<AuthMessage>('/api/v2/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, username, password }),
  })
}

export function resendVerification(email: string) {
  return api<AuthMessage>('/api/v2/auth/resend-verification', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function verifyEmail(token: string) {
  return api<AuthMessage>(`/api/v2/auth/verify-email?token=${encodeURIComponent(token)}`)
}

export function forgotPassword(email: string) {
  return api<AuthMessage>('/api/v2/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function resetPassword(token: string, newPassword: string) {
  return api<AuthMessage>('/api/v2/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  })
}

export function getMe() {
  return api<UserMe>('/api/v2/users/me')
}
