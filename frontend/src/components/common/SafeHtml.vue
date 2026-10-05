<template>
  <!-- The only application HTML sink; every value passes the shared allowlist. -->
  <!-- eslint-disable-next-line vue/no-v-html -->
  <div v-html="cleanHtml" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { sanitizeRichHtml } from '@/utils/htmlSafety'

const props = defineProps<{ html?: string | null }>()
const cleanHtml = computed(() => sanitizeRichHtml(props.html))
</script>
