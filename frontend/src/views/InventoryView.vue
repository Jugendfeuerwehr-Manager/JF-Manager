<template>
  <div class="placeholder-view">
    <Card>
      <template #content>
        <div class="placeholder-content">
          <i class="pi pi-box" style="font-size: 3rem; color: var(--primary-color);"></i>
          <h2>{{ title }}</h2>
          <p>Diese Ansicht wird noch implementiert.</p>
          <Button label="Zurück" icon="pi pi-arrow-left" @click="$router.push('/')" />
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Card from 'primevue/card'
import Button from 'primevue/button'

const route = useRoute()

const title = computed(() => {
  const titles: Record<string, string> = {
    inventory: 'Inventar',
    orders: 'Bestellungen',
    qualifications: 'Qualifikationen',
    settings: 'Einstellungen',
    profile: 'Profil'
  }
  return titles[route.name as string] || 'Seite'
})
</script>

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
