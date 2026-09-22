# Fase 4 — Frontend Development Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vue 3 + Vite chat UI dengan login, kirim pesan, upload file, render markdown, tampilkan source citation, loading state, dan error handling — terhubung ke backend Fase 2/3.

**Architecture:** Vite + Vue 3 (Composition API) + Tailwind. Pinia store `auth` menyimpan JWT di memory + localStorage. Axios instance (`services/api.js`) attach `Authorization` header otomatis. Router guard redirect ke `/login` jika belum auth. Chat state (messages array) dikelola lokal di `ChatBox.vue` via composable, tidak perlu store terpisah (YAGNI — hanya satu view chat aktif).

**Tech Stack:** Vite, Vue 3, Vue Router, Pinia, Axios, TailwindCSS, `marked` (markdown rendering).

**Spec:** `docs/superpowers/specs/2026-09-21-agentic-rag-local-design.md` (section 7)

## Global Constraints

- Semua request API (kecuali login/register) harus membawa `Authorization: Bearer <token>`.
- CORS backend mengizinkan origin `http://localhost:5173` (sudah dikonfigurasi Fase 2).
- Tidak ada refresh token — jika 401, redirect ke `/login`.

---

### Task 1: Scaffold Vite + Vue project

**Files:**
- Create: `frontend/` (via `npm create vite`)
- Modify: `frontend/tailwind.config.js`, `frontend/src/style.css` (Tailwind setup)

**Interfaces:** None (scaffolding task)

- [ ] **Step 1: Create Vite project**

Run: `npm create vite@latest frontend -- --template vue`
Expected: `frontend/` directory created with Vue 3 template.

- [ ] **Step 2: Install dependencies**

Run:
```bash
cd frontend
npm install
npm install axios vue-router pinia marked
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

- [ ] **Step 3: Configure `frontend/tailwind.config.js`**

```javascript
export default {
  content: ["./index.html", "./src/**/*.{vue,js}"],
  theme: { extend: {} },
  plugins: [],
}
```

- [ ] **Step 4: Write `frontend/src/style.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 5: Verify dev server starts**

Run: `npm run dev`
Expected: server starts at `http://localhost:5173`, default Vite+Vue page loads in browser.

Stop server (Ctrl+C) after verifying.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "Scaffold Vite + Vue 3 + Tailwind frontend"
```

---

### Task 2: API service and auth store

**Files:**
- Create: `frontend/src/services/api.js`
- Create: `frontend/src/stores/auth.js`
- Modify: `frontend/src/main.js`

**Interfaces:**
- Produces: `api` (axios instance, base URL `http://localhost:8000`, auto-attaches `Authorization` header from auth store, redirects to `/login` on 401 response).
- Produces: Pinia store `useAuthStore()` with state `{token, username, role}`, actions `login(username, password)`, `register(username, password)`, `logout()`, getter `isAuthenticated`.

- [ ] **Step 1: Write `frontend/src/stores/auth.js`**

```javascript
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
```

- [ ] **Step 2: Write `frontend/src/services/api.js`**

```javascript
import axios from 'axios'
import { useAuthStore } from '../stores/auth'
import router from '../router'

const api = axios.create({ baseURL: 'http://localhost:8000' })

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 3: Modify `frontend/src/main.js`**

```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

- [ ] **Step 4: Manual verify (no automated test — see Fase 5 for e2e)**

This task has no backend to hit yet without a router; verification happens in Task 3 (router) and Task 4 (login view) together.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/auth.js frontend/src/services/api.js frontend/src/main.js
git commit -m "Add auth store and API service with JWT interceptor"
```

---

### Task 3: Router with auth guard

**Files:**
- Create: `frontend/src/router/index.js`

**Interfaces:**
- Consumes: `useAuthStore` (Task 2).
- Produces: default export `router` (Vue Router instance) with routes `/login` (LoginView) and `/` (ChatView), navigation guard redirecting unauthenticated users to `/login`.

- [ ] **Step 1: Write `frontend/src/router/index.js`**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import LoginView from '../views/LoginView.vue'
import ChatView from '../views/ChatView.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginView },
  { path: '/', name: 'chat', component: ChatView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.name !== 'login' && !auth.isAuthenticated) {
    return { name: 'login' }
  }
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'chat' }
  }
})

export default router
```

- [ ] **Step 2: Commit** (bundled with Task 4/5 since `LoginView`/`ChatView` don't exist yet — commit after Task 5)

---

### Task 4: Login view

**Files:**
- Create: `frontend/src/views/LoginView.vue`

**Interfaces:**
- Consumes: `useAuthStore` (Task 2).

- [ ] **Step 1: Write `frontend/src/views/LoginView.vue`**

```vue
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
```

- [ ] **Step 2: Commit** (bundled with Task 3/5)

---

### Task 5: Chat view with message bubble, upload, markdown, sources

**Files:**
- Create: `frontend/src/views/ChatView.vue`
- Create: `frontend/src/components/MessageBubble.vue`
- Create: `frontend/src/components/UploadButton.vue`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `api` (Task 2 service), `useAuthStore` (Task 2).

- [ ] **Step 1: Write `frontend/src/components/MessageBubble.vue`**

```vue
<script setup>
import { marked } from 'marked'
import { computed } from 'vue'

const props = defineProps({
  role: { type: String, required: true },
  message: { type: String, required: true },
  sources: { type: Array, default: () => [] },
})

const renderedHtml = computed(() => marked.parse(props.message))
</script>

<template>
  <div :class="['my-2 rounded-lg p-3', role === 'user' ? 'ml-auto bg-blue-100' : 'mr-auto bg-gray-100']" style="max-width: 80%">
    <div class="prose prose-sm" v-html="renderedHtml"></div>
    <div v-if="sources.length" class="mt-2 text-xs text-gray-500">
      Source: {{ sources.map((s) => s.filename).join(', ') }}
    </div>
  </div>
</template>
```

- [ ] **Step 2: Write `frontend/src/components/UploadButton.vue`**

```vue
<script setup>
import { ref } from 'vue'
import api from '../services/api'

const emit = defineEmits(['uploaded', 'error'])
const uploading = ref(false)

async function handleFileChange(event) {
  const file = event.target.files[0]
  if (!file) return
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const resp = await api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    emit('uploaded', resp.data)
  } catch (e) {
    emit('error', e.response?.data?.detail || 'Upload gagal')
  } finally {
    uploading.value = false
    event.target.value = ''
  }
}
</script>

<template>
  <label class="cursor-pointer rounded px-2 py-1 text-lg" :class="{ 'opacity-50': uploading }">
    📎
    <input type="file" class="hidden" :disabled="uploading" @change="handleFileChange" />
  </label>
</template>
```

- [ ] **Step 3: Write `frontend/src/views/ChatView.vue`**

```vue
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
```

- [ ] **Step 4: Write `frontend/src/App.vue`**

```vue
<script setup>
</script>

<template>
  <router-view />
</template>
```

- [ ] **Step 5: Manual verification**

Run backend (Fase 1-3 must be running: Postgres, Ollama, `uvicorn app.main:app --port 8000`), then:
Run: `cd frontend && npm run dev`
Open `http://localhost:5173` in browser.

Verify manually:
- Redirected to `/login` when not authenticated.
- Register a user via backend (`curl -X POST http://localhost:8000/auth/register ...`) or add a temporary register link — for MVP, registration is done via API directly (no register UI per Task scope); login with that user.
- After login, redirected to `/` (chat view).
- Send a message → assistant response renders as markdown.
- Upload a `.txt` file → confirmation message appears.
- Ask a question referencing uploaded content → answer includes source citation.
- Logout → redirected to `/login`, token cleared from localStorage.

- [ ] **Step 6: Commit** (Tasks 3, 4, 5 together since they're interdependent views)

```bash
git add frontend/src/router/ frontend/src/views/ frontend/src/components/ frontend/src/App.vue
git commit -m "Add login view, chat view, message bubble, and upload button"
```

---

## Definition of Done for Fase 4

- [ ] Unauthenticated user redirected to `/login`.
- [ ] Login stores JWT and redirects to chat view.
- [ ] Chat sends message, displays markdown-rendered response with loading state.
- [ ] Upload button sends file to `/upload`, shows confirmation.
- [ ] Source citation displayed when `sources` non-empty.
- [ ] 401 response (expired token) redirects to `/login` and clears stored token.
- [ ] Error from backend (e.g. network failure) shown to user, doesn't crash the view.
