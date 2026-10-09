<template>
  <header class="workspace-head">
    <div class="workspace-head__info">
      <p class="workspace-head__eyebrow">
        <router-link :to="backTo" class="workspace-head__back"><i class="pi pi-arrow-left" aria-hidden="true"></i>{{ backLabel }}</router-link>
        <span v-if="eyebrow"> · {{ eyebrow }}</span>
      </p>
      <h1 class="workspace-head__title">{{ title }}</h1>
      <div v-if="$slots.meta" class="workspace-head__meta"><slot name="meta" /></div>
    </div>
    <div class="workspace-head__actions">
      <slot name="status" />
      <Button
        :icon="navHidden ? 'pi pi-window-minimize' : 'pi pi-window-maximize'"
        severity="secondary"
        text
        class="workspace-head__nav-toggle"
        :aria-label="navHidden ? 'Navigation einblenden' : 'Navigation ausblenden, mehr Platz zum Bearbeiten'"
        :aria-pressed="navHidden"
        v-tooltip.bottom="navHidden ? 'Navigation einblenden' : 'Mehr Platz: Navigation ausblenden'"
        @click="toggleNav"
      />
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import type { RouteLocationRaw } from 'vue-router'
import { useWorkspaceNavigation } from '@/composables/useWorkspaceNavigation'

/** Header for workspace routes (meta.workspace): back link, title and the shared "hide navigation" toggle. */
defineProps<{
  title: string
  backTo: RouteLocationRaw
  backLabel: string
  eyebrow?: string
}>()

const { navHidden, toggleNav } = useWorkspaceNavigation()
</script>

<style scoped>
.workspace-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5) var(--jf-space-3);
  padding: var(--jf-space-1-5) var(--jf-space-3);
  background: var(--jf-color-card);
  border-bottom: 1px solid var(--jf-color-border);
  flex-shrink: 0;
}
.workspace-head__info { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.workspace-head__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}
.workspace-head__back {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  color: var(--jf-color-primary);
  text-decoration: none;
}
.workspace-head__back i { font-size: 0.7rem; }
.workspace-head__title {
  margin: 0;
  font-size: var(--jf-text-xl);
  line-height: var(--jf-leading-tight);
  letter-spacing: -0.015em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.workspace-head__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}
.workspace-head__actions { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-1); }
/* The navigation can only be hidden next to the desktop sidebar. */
@media (max-width: 1023px) { .workspace-head__nav-toggle { display: none; } }
@media (max-width: 480px) { .workspace-head { padding: var(--jf-space-1-5) var(--jf-space-2); } }
</style>
