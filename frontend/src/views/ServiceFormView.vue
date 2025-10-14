<template>
  <div class="service-detail-view">
    <Toolbar class="view-toolbar">
      <template #start>
        <Button icon="pi pi-arrow-left" text @click="handleBack" class="mr-2" />
        <div class="toolbar-title">
          <h1>Dienst bearbeiten</h1>
        </div>
      </template>
    </Toolbar>

    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <Message v-else-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <div v-else class="form-layout">
      <Card class="form-card">
        <template #title>Dienst-Details</template>
        <template #content>
          <ServiceForm
            :initial-data="servicebookStore.currentService"
            :loading="saving"
            :submit-label="isEdit ? 'Aktualisieren' : 'Erstellen'"
            @submit="handleSubmit"
            @cancel="handleBack"
          />
        </template>
      </Card>

      <Card v-if="isEdit && serviceId !== null && servicebookStore.currentService" class="attendance-card">
        <template #title>Anwesenheit</template>
        <template #content>
          <AttendanceManager :service-id="serviceId" />
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Toolbar from 'primevue/toolbar'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import ServiceForm from '@/components/servicebook/organisms/ServiceForm.vue'
import AttendanceManager from '@/components/servicebook/organisms/AttendanceManager.vue'
import { useServicebookStore } from '@/stores/servicebook'
import type { ServiceFormData } from '@/types/servicebook'

const router = useRouter()
const route = useRoute()
const toast = useToast()
const servicebookStore = useServicebookStore()

const serviceId = computed(() => {
  const id = route.params.id
  return id ? parseInt(id as string) : null
})

const isEdit = computed(() => serviceId.value !== null)

const loading = ref(false)
const error = ref<string | null>(null)
const saving = ref(false)

onMounted(async () => {
  if (isEdit.value && serviceId.value) {
    loading.value = true
    try {
      await servicebookStore.fetchService(serviceId.value)
    } catch (err: any) {
      error.value = err.message || 'Fehler beim Laden des Dienstes'
    } finally {
      loading.value = false
    }
  }
})

const handleSubmit = async (data: ServiceFormData) => {
  saving.value = true
  try {
    if (isEdit.value && serviceId.value) {
      await servicebookStore.updateService(serviceId.value, data)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Dienst wurde aktualisiert',
        life: 3000
      })
    } else {
      const created = await servicebookStore.createService(data)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Dienst wurde erstellt',
        life: 3000
      })
      // Navigate to edit view and load the service details
      await router.push({ name: 'service-edit', params: { id: created.id } })
      // Reload the service to get full details including attendees
      await servicebookStore.fetchService(created.id)
      return
    }
  } catch (err: any) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: err.message || 'Fehler beim Speichern des Dienstes',
      life: 5000
    })
  } finally {
    saving.value = false
  }
}

const handleBack = () => {
  router.push({ name: 'servicebook' })
}
</script>

<style scoped>
.view-toolbar {
  margin-bottom: 1.5rem;
  border-radius: var(--border-radius);
}

.toolbar-title h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 600;
}

@media (max-width: 768px) {
  .view-toolbar {
    position: sticky;
    top: 0;
    z-index: 100;
    margin-bottom: 1rem;
    border-radius: 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.form-layout {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 1.5rem;
}

.form-card,
.attendance-card {
  height: fit-content;
}

.attendance-card {
  position: sticky;
  top: 1rem;
  max-height: calc(100vh - 2rem);
  overflow: hidden;
  overflow-y: auto;
}

@media (max-width: 1024px) {
  .form-layout {
    grid-template-columns: 1fr;
  }

  .attendance-card {
    position: relative;
    top: auto;
    max-height: none;
  }
}
</style>
