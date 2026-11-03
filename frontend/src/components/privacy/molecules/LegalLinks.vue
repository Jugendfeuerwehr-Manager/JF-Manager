<template>
  <span v-if="legal?.imprint || legal?.privacy || legal?.portal_terms" class="legal-links">
    <RouterLink v-if="legal.imprint" to="/impressum">Impressum</RouterLink>
    <RouterLink v-if="legal.privacy" to="/datenschutz">Datenschutz</RouterLink>
    <RouterLink v-if="legal.portal_terms" to="/nutzungsregeln">Nutzungsregeln</RouterLink>
  </span>
</template>

<script setup lang="ts">
import type { PublicBranding } from '@/types/settings'

interface Props {
  /** Published legal texts, from the public branding endpoint. */
  legal?: PublicBranding['legal'] | null
}

defineProps<Props>()
</script>

<style scoped>
.legal-links { display: inline-flex; gap: 1rem; font-size: .85rem; }
.legal-links a { color: inherit; opacity: .85; }
.legal-links a:hover { opacity: 1; }
</style>
