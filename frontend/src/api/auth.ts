import { api } from './http'
import type { UserMe } from './types'

type TokenResponse = { access_token: string; token_type: string }

export function login(identifier: string, password: string) {
  return api<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ identifier, password }),
  })
}

export function register(email: string, username: string, password: string) {
  return api<TokenResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, username, password }),
  })
}

export function getMe() {
  return api<UserMe>('/api/v1/users/me')
}
