<script setup lang="ts">
defineProps<{ icon: string, title: string, text: string }>()
</script>

<template>
  <section class="portal-empty" :aria-label="title">
    <i :class="icon" aria-hidden="true"></i>
    <h1>{{ title }}</h1>
    <p>{{ text }}</p>
  </section>
</template>

<style scoped>
.portal-empty { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 0.5rem; padding: 2.5rem 1rem; color: var(--p-text-muted-color); }
.portal-empty i { font-size: 2rem; }
.portal-empty h1 { margin: 0; font-size: 1.25rem; color: var(--p-text-color); }
.portal-empty p { margin: 0; max-width: 28rem; }
</style>
