import { defineStore } from 'pinia'
import * as authApi from '../api/v2/auth'
import type { UserMe } from '../api/types'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as UserMe | null,
    token: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token'),
  }),
  actions: {
    async login(identifier: string, password: string) {
      const data = await authApi.login(identifier, password)
      this.token = data.access_token
      this.refreshToken = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      await this.loadMe()
    },
    async register(email: string, username: string, password: string) {
      const data = await authApi.register(email, username, password)
      this.token = data.access_token
      this.refreshToken = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      await this.loadMe()
    },
    async loadMe() {
      this.token = localStorage.getItem('access_token')
      this.refreshToken = localStorage.getItem('refresh_token')
      if (!this.token && !this.refreshToken) return
      this.user = await authApi.getMe()
      this.token = localStorage.getItem('access_token')
      this.refreshToken = localStorage.getItem('refresh_token')
    },
    logout() {
      this.user = null
      this.token = null
      this.refreshToken = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    },
  },
})
