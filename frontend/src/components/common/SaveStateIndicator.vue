<template>
  <span class="save-state" :class="`save-state--${state}`" role="status">
    <i :class="meta.icon" aria-hidden="true"></i>{{ text ?? meta.text }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

/**
 * One save/sync indicator for collaborative entry (lists, attendance).
 * A failed or refused write is never shown as saved; a conflict says that
 * the current server state is now shown instead of the own change.
 */
export type SaveState = 'loading' | 'saving' | 'saved' | 'error' | 'offline' | 'conflict'

const props = withDefaults(defineProps<{ state: SaveState; text?: string }>(), { text: undefined })

const STATES: Record<SaveState, { icon: string; text: string }> = {
  loading: { icon: 'pi pi-spin pi-spinner', text: 'Wird geladen …' },
  saving: { icon: 'pi pi-spin pi-spinner', text: 'Speichert …' },
  saved: { icon: 'pi pi-check', text: 'Gespeichert' },
  error: { icon: 'pi pi-exclamation-triangle', text: 'Nicht gespeichert' },
  offline: { icon: 'pi pi-wifi', text: 'Offline – Abgleich unterbrochen' },
  conflict: { icon: 'pi pi-sync', text: 'Aktueller Stand übernommen' },
}

const meta = computed(() => STATES[props.state])
</script>

<style scoped>
.save-state {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  background: var(--p-green-100);
  color: var(--p-green-800);
}
.save-state--saving,
.save-state--loading { background: var(--surface-hover); color: var(--jf-color-text-muted); }
.save-state--error,
.save-state--offline { background: var(--p-red-100); color: var(--p-red-800); }
.save-state--conflict { background: var(--p-amber-100); color: var(--p-amber-900); }
.app-dark .save-state { background: color-mix(in srgb, var(--p-green-400), transparent 84%); color: var(--p-green-300); }
.app-dark .save-state--saving,
.app-dark .save-state--loading { background: var(--surface-hover); color: var(--jf-color-text-muted); }
.app-dark .save-state--error,
.app-dark .save-state--offline { background: color-mix(in srgb, var(--p-red-400), transparent 84%); color: var(--p-red-300); }
.app-dark .save-state--conflict { background: color-mix(in srgb, var(--p-amber-400), transparent 84%); color: var(--p-amber-300); }
</style>
