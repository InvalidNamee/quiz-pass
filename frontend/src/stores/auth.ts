import { defineStore } from 'pinia'
import { api, type UserMe } from '../api/client'

type TokenResponse = { access_token: string; token_type: string }

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as UserMe | null,
    token: localStorage.getItem('access_token'),
  }),
  actions: {
    async login(identifier: string, password: string) {
      const data = await api<TokenResponse>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ identifier, password }),
      })
      this.token = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await this.loadMe()
    },
    async register(email: string, username: string, password: string) {
      const data = await api<TokenResponse>('/api/v1/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, username, password }),
      })
      this.token = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await this.loadMe()
    },
    async loadMe() {
      if (!this.token) return
      this.user = await api<UserMe>('/api/v1/users/me')
    },
    logout() {
      this.user = null
      this.token = null
      localStorage.removeItem('access_token')
    },
  },
})
