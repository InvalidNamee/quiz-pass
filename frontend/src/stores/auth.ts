import { defineStore } from 'pinia'
import * as authApi from '../api/auth'
import type { UserMe } from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as UserMe | null,
    token: localStorage.getItem('access_token'),
  }),
  actions: {
    async login(identifier: string, password: string) {
      const data = await authApi.login(identifier, password)
      this.token = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await this.loadMe()
    },
    async register(email: string, username: string, password: string) {
      const data = await authApi.register(email, username, password)
      this.token = data.access_token
      localStorage.setItem('access_token', data.access_token)
      await this.loadMe()
    },
    async loadMe() {
      if (!this.token) return
      this.user = await authApi.getMe()
    },
    logout() {
      this.user = null
      this.token = null
      localStorage.removeItem('access_token')
    },
  },
})
