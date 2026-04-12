<template>
  <span
    class="permission-info"
    v-tooltip.top="description || 'Keine Beschreibung verfügbar'"
  >
    <i class="pi pi-question-circle"></i>
  </span>
</template>

<script setup lang="ts">
defineProps<{
  description: string
}>()
</script>

<style scoped>
.permission-info {
  cursor: help;
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  margin-left: 0.35rem;
}

.permission-info:hover {
  color: var(--p-primary-color);
}
</style>
