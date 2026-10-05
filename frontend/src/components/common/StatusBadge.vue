<template>
  <span class="status-badge" :class="`status-badge--${severity}`">
    <i :class="icon ?? icons[severity]" aria-hidden="true"></i>
    <span>{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
export type StatusSeverity = 'success' | 'info' | 'warning' | 'danger' | 'neutral'

withDefaults(defineProps<{
  label: string
  severity?: StatusSeverity
  /** Overrides the default symbol; colour alone never carries the meaning. */
  icon?: string
}>(), { severity: 'neutral', icon: undefined })

const icons: Record<StatusSeverity, string> = {
  success: 'pi pi-check-circle',
  info: 'pi pi-info-circle',
  warning: 'pi pi-exclamation-triangle',
  danger: 'pi pi-times-circle',
  neutral: 'pi pi-circle',
}
</script>

<style scoped>
.status-badge {
  --badge-fg: var(--jf-color-text-muted);
  --badge-bg: var(--surface-hover);
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  padding: 2px var(--jf-space-1);
  border-radius: 999px;
  background: var(--badge-bg);
  color: var(--badge-fg);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  line-height: 1.5;
  white-space: nowrap;
}

.status-badge i {
  font-size: 0.8em;
}

.status-badge--success { --badge-fg: var(--p-green-800); --badge-bg: var(--p-green-100); }
.status-badge--info { --badge-fg: var(--p-sky-800); --badge-bg: var(--p-sky-100); }
.status-badge--warning { --badge-fg: var(--p-amber-800); --badge-bg: var(--p-amber-100); }
.status-badge--danger { --badge-fg: var(--p-red-800); --badge-bg: var(--p-red-100); }

.app-dark .status-badge--success { --badge-fg: var(--p-green-300); --badge-bg: color-mix(in srgb, var(--p-green-400), transparent 84%); }
.app-dark .status-badge--info { --badge-fg: var(--p-sky-300); --badge-bg: color-mix(in srgb, var(--p-sky-400), transparent 84%); }
.app-dark .status-badge--warning { --badge-fg: var(--p-amber-300); --badge-bg: color-mix(in srgb, var(--p-amber-400), transparent 84%); }
.app-dark .status-badge--danger { --badge-fg: var(--p-red-300); --badge-bg: color-mix(in srgb, var(--p-red-400), transparent 84%); }
</style>
