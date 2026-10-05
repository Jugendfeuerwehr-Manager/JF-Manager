<template>
  <div class="state-view" :class="`state-view--${kind}`" :role="kind === 'error' || kind === 'offline' ? 'alert' : 'status'" :aria-busy="kind === 'loading' || undefined">
    <span class="state-view__icon" aria-hidden="true">
      <i :class="kind === 'loading' ? 'pi pi-spin pi-spinner' : content.icon"></i>
    </span>
    <h2 class="state-view__title">{{ title ?? content.title }}</h2>
    <p v-if="message ?? content.message" class="state-view__message">{{ message ?? content.message }}</p>
    <div v-if="$slots.default || showRetry" class="state-view__actions">
      <slot />
      <Button v-if="showRetry" label="Erneut versuchen" icon="pi pi-refresh" severity="secondary" outlined @click="$emit('retry')" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import type { ApiErrorKind } from '@/utils/apiError'

export type StateKind = 'loading' | 'empty' | 'forbidden' | 'offline' | 'error'

const props = withDefaults(defineProps<{
  kind: StateKind
  title?: string
  message?: string
  /** Offer "Erneut versuchen"; defaults to on for offline and error. */
  retry?: boolean
}>(), { title: undefined, message: undefined, retry: undefined })

defineEmits<{ retry: [] }>()

const defaults: Record<StateKind, { icon: string; title: string; message?: string }> = {
  loading: { icon: 'pi pi-spinner', title: 'Wird geladen …' },
  empty: { icon: 'pi pi-inbox', title: 'Noch keine Einträge', message: 'Sobald Daten vorhanden sind, erscheinen sie hier.' },
  forbidden: { icon: 'pi pi-lock', title: 'Keine Berechtigung', message: 'Dir fehlt das Recht für diesen Bereich. Wende dich bei Bedarf an deine Jugendfeuerwehrleitung.' },
  offline: { icon: 'pi pi-wifi', title: 'Keine Verbindung', message: 'Der Server ist nicht erreichbar. Bereits eingegebene Daten bleiben erhalten.' },
  error: { icon: 'pi pi-exclamation-triangle', title: 'Laden fehlgeschlagen', message: 'Beim Laden ist ein Fehler aufgetreten.' },
}

const content = computed(() => defaults[props.kind])
const showRetry = computed(() => props.retry ?? (props.kind === 'offline' || props.kind === 'error'))
</script>

<script lang="ts">
/** Maps an API error onto the state the view should show. */
export function stateForError(kind: ApiErrorKind): 'forbidden' | 'offline' | 'error' {
  if (kind === 'forbidden') return 'forbidden'
  if (kind === 'network') return 'offline'
  return 'error'
}
</script>

<style scoped>
.state-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--jf-space-1);
  padding: var(--jf-space-5) var(--jf-space-3);
  text-align: center;
  border: 1px dashed var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.state-view__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin-bottom: var(--jf-space-0-5);
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--jf-color-text-muted);
  font-size: 1.25rem;
}

.state-view--forbidden .state-view__icon,
.state-view--error .state-view__icon {
  background: var(--jf-color-selected);
  color: var(--jf-color-primary);
}

.state-view__title {
  margin: 0;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}

.state-view__message {
  margin: 0;
  max-width: 44ch;
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
}

.state-view__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--jf-space-1);
  margin-top: var(--jf-space-1);
}
</style>
