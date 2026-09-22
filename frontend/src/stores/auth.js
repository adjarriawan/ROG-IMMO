import { defineStore } from 'pinia'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
    username: localStorage.getItem('username') || null,
    role: localStorage.getItem('role') || null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const resp = await axios.post(`${API_BASE}/auth/login`, { username, password })
      this.token = resp.data.access_token
      this.username = username
      localStorage.setItem('token', this.token)
      localStorage.setItem('username', username)
    },
    async register(username, password) {
      await axios.post(`${API_BASE}/auth/register`, { username, password })
    },
    logout() {
      this.token = null
      this.username = null
      this.role = null
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('role')
    },
  },
})
