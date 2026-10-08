<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

withDefaults(defineProps<{ icon?: string, to?: RouteLocationRaw }>(), { icon: 'pi pi-info-circle', to: undefined })
</script>

<template>
  <component :is="to ? 'RouterLink' : 'div'" :to="to" class="portal-notice">
    <i :class="icon" class="lead" aria-hidden="true"></i>
    <span class="text"><slot /></span>
    <i v-if="to" class="pi pi-chevron-right" aria-hidden="true"></i>
  </component>
</template>

<style scoped>
.portal-notice { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-radius: 12px; font-size: 14px; text-decoration: none; background: var(--p-blue-50); border: 1px solid var(--p-blue-200); color: var(--p-blue-900); }
.lead { font-size: 18px; }
.text { flex: 1; min-width: 0; }
.app-dark .portal-notice { background: color-mix(in srgb, var(--p-blue-400), transparent 88%); border-color: color-mix(in srgb, var(--p-blue-400), transparent 60%); color: var(--p-blue-200); }
</style>
