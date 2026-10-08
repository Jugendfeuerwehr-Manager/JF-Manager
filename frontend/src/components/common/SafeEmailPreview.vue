<template>
  <iframe
    title="E-Mail-Vorschau"
    sandbox=""
    referrerpolicy="no-referrer"
    :srcdoc="documentHtml"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sanitizeRichHtml } from '@/utils/htmlSafety'

const props = defineProps<{ html?: string | null }>()
const documentHtml = computed(() => `<!doctype html><html lang="de"><head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; base-uri 'none'; form-action 'none'; style-src 'unsafe-inline'">
<style>body { font-family: sans-serif; overflow-wrap: anywhere; padding: 12px; } table { max-width: 100%; }</style>
</head><body>${sanitizeRichHtml(props.html, true)}</body></html>`)
</script>

<style scoped>
iframe { display: block; width: 100%; min-height: 24rem; border: 0; background: white; }
</style>
