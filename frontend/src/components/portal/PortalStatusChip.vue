<script setup lang="ts">
import { computed } from 'vue'

export type PortalStatus = 'expected' | 'no-response' | 'declined' | 'unavailable' | 'registered' | 'waitlist' | 'assigned'

const props = defineProps<{ status: PortalStatus }>()

const variants: Record<PortalStatus, { label: string, icon: string, tone: string }> = {
  expected: { label: 'Erwartet', icon: 'pi pi-check', tone: 'success' },
  'no-response': { label: 'Keine Rückmeldung', icon: 'pi pi-circle', tone: 'neutral' },
  declined: { label: 'Abgemeldet', icon: 'pi pi-times', tone: 'warning' },
  unavailable: { label: 'Nicht möglich', icon: 'pi pi-lock', tone: 'neutral' },
  registered: { label: 'Angemeldet', icon: 'pi pi-check', tone: 'success' },
  waitlist: { label: 'Warteliste', icon: 'pi pi-clock', tone: 'info' },
  assigned: { label: 'Zugeteilt', icon: 'pi pi-check-circle', tone: 'success' },
}
const variant = computed(() => variants[props.status])
</script>

<template>
  <span class="portal-chip" :class="`portal-chip--${variant.tone}`" :data-status="status">
    <i :class="variant.icon" aria-hidden="true"></i>{{ variant.label }}
  </span>
</template>

<style scoped>
.portal-chip { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; font-size: 12px; font-weight: 650; padding: 4px 8px; border-radius: 999px; background: var(--chip-bg); color: var(--chip-fg); }
.portal-chip i { font-size: 11px; }
.portal-chip--success { --chip-fg: var(--p-green-800); --chip-bg: var(--p-green-100); }
.portal-chip--warning { --chip-fg: var(--p-orange-800); --chip-bg: var(--p-orange-100); }
.portal-chip--info { --chip-fg: var(--p-sky-800); --chip-bg: var(--p-sky-100); }
.portal-chip--neutral { --chip-fg: var(--p-surface-700); --chip-bg: var(--p-surface-100); }
.app-dark .portal-chip--success { --chip-fg: var(--p-green-300); --chip-bg: color-mix(in srgb, var(--p-green-400), transparent 84%); }
.app-dark .portal-chip--warning { --chip-fg: var(--p-orange-300); --chip-bg: color-mix(in srgb, var(--p-orange-400), transparent 84%); }
.app-dark .portal-chip--info { --chip-fg: var(--p-sky-300); --chip-bg: color-mix(in srgb, var(--p-sky-400), transparent 84%); }
.app-dark .portal-chip--neutral { --chip-fg: var(--p-surface-200); --chip-bg: var(--p-surface-800); }
</style>
