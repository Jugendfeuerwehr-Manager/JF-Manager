<template>
  <div class="servicebook-view">
    <div class="view-header">
      <div>
        <h1>Dienstbuch</h1>
        <p>Verwaltung der Dienste und Einsätze</p>
      </div>
      <Button
        :label="isMobile ? '' : 'Neuer Dienst'"
        icon="pi pi-plus"
        severity="primary"
      />
    </div>

    <Card>
      <template #content>
        <p class="text-center text-color-secondary p-5">
          Dienstbuch-Ansicht wird noch implementiert.
        </p>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'

const isMobile = ref(window.innerWidth < 768)

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.servicebook-view {
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

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.view-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-color);
  margin: 0 0 0.25rem 0;
}

.view-header p {
  color: var(--text-color-secondary);
  margin: 0;
  font-size: 0.875rem;
}

@media (max-width: 767px) {
  .view-header h1 {
    font-size: 1.5rem;
  }
}
</style>
