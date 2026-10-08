<template>
  <span class="scope-badge" :title="hint">
    <i class="pi pi-building" aria-hidden="true"></i>
    <span>Zentral</span>
    <span class="visually-hidden">: {{ hint }}</span>
  </span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  /** Explains the scope; shown as tooltip and read by screen readers. */
  hint?: string
}>(), { hint: 'gehört der Organisation, nicht einer Abteilung' })
</script>

<style scoped>
.scope-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 1px 8px;
  border: 1px solid var(--jf-color-border);
  border-radius: 999px;
  background: var(--jf-color-ground);
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-semibold);
  line-height: 1.5;
  white-space: nowrap;
}

.scope-badge i {
  font-size: 0.7rem;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
