<template>
  <button
    :type="type"
    class="adm-button"
    :class="[`adm-button--${variant}`, { 'adm-button--icon-only': !$slots.default && icon }]"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <i v-if="loading" class="pi pi-spin pi-spinner" aria-hidden="true"></i>
    <i v-else-if="icon" :class="icon" aria-hidden="true"></i>
    <span v-if="$slots.default"><slot /></span>
  </button>
</template>

<script setup lang="ts">
interface Props {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  type?: 'button' | 'submit'
  icon?: string
  disabled?: boolean
  loading?: boolean
}

withDefaults(defineProps<Props>(), { variant: 'secondary', type: 'button', icon: '', disabled: false, loading: false })
</script>

<style scoped>
.adm-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  font: inherit;
  font-weight: var(--jf-weight-medium);
  cursor: pointer;
  transition: background var(--jf-duration, 120ms), border-color var(--jf-duration, 120ms);
}

.adm-button:hover:not(:disabled) {
  border-color: var(--jf-color-primary);
}

.adm-button:focus-visible {
  outline: none;
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.adm-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.adm-button--primary {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.adm-button--ghost {
  border-color: transparent;
  background: transparent;
}

.adm-button--danger {
  border-color: transparent;
  background: transparent;
  color: var(--jf-color-danger);
}

.adm-button--icon-only {
  width: var(--jf-touch-target, 44px);
  padding: 0;
}
</style>
