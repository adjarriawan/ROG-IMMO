<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Login gagal'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-100">
    <form @submit.prevent="handleLogin" class="w-full max-w-sm rounded-lg bg-white p-6 shadow">
      <h1 class="mb-4 text-xl font-semibold">Agentic RAG Assistant</h1>
      <input v-model="username" type="text" placeholder="Username" class="mb-3 w-full rounded border p-2" />
      <input v-model="password" type="password" placeholder="Password" class="mb-3 w-full rounded border p-2" />
      <p v-if="error" class="mb-3 text-sm text-red-600">{{ error }}</p>
      <button type="submit" :disabled="loading" class="w-full rounded bg-blue-600 p-2 text-white disabled:opacity-50">
        {{ loading ? 'Loading...' : 'Login' }}
      </button>
    </form>
  </div>
</template>
