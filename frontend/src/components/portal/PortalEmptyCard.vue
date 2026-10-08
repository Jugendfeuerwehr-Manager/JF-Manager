<script setup lang="ts">
defineProps<{ icon?: string, title: string }>()
</script>

<template>
  <section class="portal-empty-card" :aria-label="title">
    <i v-if="icon" :class="icon" aria-hidden="true"></i>
    <h2>{{ title }}</h2>
    <p><slot /></p>
  </section>
</template>

<style scoped>
.portal-empty-card { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 14px; border-radius: 14px; background: var(--p-content-background); border: 1px dashed var(--p-content-border-color); color: var(--p-text-muted-color); }
.portal-empty-card i { font-size: 20px; }
h2 { margin: 0; font-size: 16px; font-weight: 650; color: var(--p-text-color); }
p { margin: 0; font-size: 14px; }
</style>
