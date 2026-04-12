<template>
  <SettingsView />
</template>

<script setup lang="ts">
import SettingsView from '@/components/settings/organisms/SettingsView.vue'
</script>

<style scoped>
/* Placeholder styles removed - actual implementation in organism component */
</style>

<style scoped>
.placeholder-view {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 4rem 2rem;
  text-align: center;
}

.placeholder-content h2 {
  margin: 0;
  color: var(--text-color);
}

.placeholder-content p {
  margin: 0;
  color: var(--text-color-secondary);
}
</style>
