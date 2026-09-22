<script setup>
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { computed } from 'vue'

const props = defineProps({
  role: { type: String, required: true },
  message: { type: String, required: true },
  sources: { type: Array, default: () => [] },
})

const renderedHtml = computed(() => DOMPurify.sanitize(marked.parse(props.message)))
</script>

<template>
  <div :class="['my-2 rounded-lg p-3', role === 'user' ? 'ml-auto bg-blue-100' : 'mr-auto bg-gray-100']" style="max-width: 80%">
    <div class="prose prose-sm" v-html="renderedHtml"></div>
    <div v-if="sources.length" class="mt-2 text-xs text-gray-500">
      Source: {{ sources.map((s) => s.filename).join(', ') }}
    </div>
  </div>
</template>
