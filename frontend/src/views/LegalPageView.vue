<template>
  <main class="legal-page">
    <article class="legal-page__card">
      <ProgressSpinner v-if="privacyStore.publicLoading" />
      <Message v-else-if="privacyStore.publicError" severity="info" :closable="false">{{ privacyStore.publicError }}</Message>
      <template v-else-if="privacyStore.publicPage">
        <h1>{{ privacyStore.publicPage.title }}</h1>
        <!-- Server-side sanitized (nh3) and sanitized again here. -->
        <div class="legal-page__body" v-html="safeBody" />
        <p class="legal-page__meta">
          Version {{ privacyStore.publicPage.version }} · Stand {{ formatDate(privacyStore.publicPage.published_at) }}
        </p>
      </template>
      <nav class="legal-page__nav">
        <a href="#" @click.prevent="goBack">Zurück</a>
        <LegalLinks :legal="{ imprint: true, privacy: true }" />
      </nav>
    </article>
  </main>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import LegalLinks from '@/components/privacy/molecules/LegalLinks.vue'
import { usePrivacyStore } from '@/stores/privacy'
import type { LegalPageKind } from '@/types/privacy'
import { sanitizeRichHtml } from '@/utils/htmlSafety'

interface Props {
  kind: LegalPageKind
}

const props = defineProps<Props>()
const privacyStore = usePrivacyStore()
const router = useRouter()

const safeBody = computed(() => sanitizeRichHtml(privacyStore.publicPage?.body))

watch(() => props.kind, kind => {
  void privacyStore.fetchPublicPage(kind)
}, { immediate: true })

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('de-DE', { dateStyle: 'long' })
}

function goBack() {
  if (window.history.length > 1) router.back()
  else void router.push('/')
}
</script>

<style scoped>
.legal-page { min-height: 100vh; display: flex; justify-content: center; padding: 2rem 1rem; background: var(--p-surface-ground, var(--surface-ground)); }
.legal-page__card { width: 100%; max-width: 760px; background: var(--p-content-background, var(--surface-card)); border-radius: 12px; padding: 2rem; display: flex; flex-direction: column; gap: 1rem; }
.legal-page__body { line-height: 1.6; overflow-wrap: anywhere; }
.legal-page__meta { color: var(--text-color-secondary); font-size: .85rem; margin: 0; }
.legal-page__nav a { color: var(--p-primary-color); }
.legal-page__nav { display: flex; justify-content: space-between; flex-wrap: wrap; gap: .75rem; border-top: 1px solid var(--p-content-border-color); padding-top: 1rem; }
@media (max-width: 600px) { .legal-page__card { padding: 1.25rem; } }
</style>
