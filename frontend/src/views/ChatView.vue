<script setup>
import { ref } from 'vue'
import api from '../services/api'
import { useAuthStore } from '../stores/auth'
import MessageBubble from '../components/MessageBubble.vue'
import UploadButton from '../components/UploadButton.vue'

const auth = useAuthStore()
const sessionId = `session-${Date.now()}`
const messages = ref([])
const input = ref('')
const loading = ref(false)
const error = ref('')

async function sendMessage() {
  if (!input.value.trim()) return
  const userMessage = input.value
  messages.value.push({ role: 'user', message: userMessage, sources: [] })
  input.value = ''
  loading.value = true
  error.value = ''
  try {
    const resp = await api.post('/chat', { session_id: sessionId, message: userMessage })
    messages.value.push({ role: 'assistant', message: resp.data.answer, sources: resp.data.sources })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Terjadi kesalahan'
  } finally {
    loading.value = false
  }
}

function handleUploaded(data) {
  messages.value.push({ role: 'assistant', message: `File **${data.filename}** berhasil diproses.`, sources: [] })
}

function handleUploadError(msg) {
  error.value = msg
}

function handleLogout() {
  auth.logout()
  window.location.href = '/login'
}
</script>

<template>
  <div class="flex h-screen flex-col bg-gray-50">
    <header class="flex items-center justify-between border-b bg-white p-4">
      <h1 class="text-lg font-semibold">Agentic RAG Assistant</h1>
      <button @click="handleLogout" class="text-sm text-gray-500">Logout ({{ auth.username }})</button>
    </header>

    <main class="flex-1 overflow-y-auto p-4">
      <MessageBubble
        v-for="(m, i) in messages"
        :key="i"
        :role="m.role"
        :message="m.message"
        :sources="m.sources"
      />
      <p v-if="loading" class="text-sm text-gray-400">AI sedang mengetik...</p>
      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    </main>

    <footer class="flex items-center gap-2 border-t bg-white p-4">
      <UploadButton @uploaded="handleUploaded" @error="handleUploadError" />
      <input
        v-model="input"
        @keyup.enter="sendMessage"
        type="text"
        placeholder="Tulis pertanyaan..."
        class="flex-1 rounded border p-2"
      />
      <button @click="sendMessage" :disabled="loading" class="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">
        Send
      </button>
    </footer>
  </div>
</template>
