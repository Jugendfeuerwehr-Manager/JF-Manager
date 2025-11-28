<template>
  <Card class="settings-category-card">
    <template #header>
      <div class="flex align-items-center gap-2 p-3">
        <i :class="icon" class="text-2xl"></i>
        <div>
          <h3 class="m-0">{{ title }}</h3>
          <p class="text-sm text-color-secondary m-0">{{ description }}</p>
        </div>
      </div>
    </template>
    <template #content>
      <slot></slot>
    </template>
    <template #footer v-if="$slots.footer">
      <slot name="footer"></slot>
    </template>
  </Card>
</template>

<script setup lang="ts">
import Card from 'primevue/card'

interface Props {
  title: string
  description: string
  icon: string
}

defineProps<Props>()
</script>

<style scoped>
.settings-category-card {
  margin-bottom: 1rem;
}
</style>
