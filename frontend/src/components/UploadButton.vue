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
