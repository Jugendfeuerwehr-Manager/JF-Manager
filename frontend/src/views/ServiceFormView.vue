<template>
  <div class="service-edit">
    <nav aria-label="Brotkrumen" class="breadcrumb">
      <router-link :to="{ name: 'servicebook' }">Dienstbuch</router-link>
      <i class="pi pi-angle-right" aria-hidden="true"></i>
      <span aria-current="page">{{ isEdit ? 'Dienst bearbeiten' : 'Neuer Dienst' }}</span>
    </nav>

    <StateView v-if="loading" kind="loading" title="Dienst wird geladen …" />
    <StateView v-else-if="error" kind="error" title="Dienst konnte nicht geladen werden" :message="error" :retry="false" />

    <template v-else>
      <header class="edit-head">
        <p v-if="dateLine" class="edit-head__eyebrow">{{ dateLine }}</p>
        <h1>{{ isEdit ? (service?.topic || 'Dienst ohne Thema') : 'Neuer Dienst' }}</h1>
        <p v-if="isEdit && service?.place" class="edit-head__meta">{{ service.place }}</p>
      </header>

      <DeleteServiceButton v-if="service" :service="service" :disabled="saving" />

      <div v-if="isEdit" class="segmented" role="tablist" aria-label="Bereich" @keydown.left.prevent="switchByKey" @keydown.right.prevent="switchByKey">
        <button
          id="tab-details"
          type="button"
          role="tab"
          :aria-selected="tab === 'details'"
          :tabindex="tab === 'details' ? 0 : -1"
          aria-controls="panel-details"
          @click="setTab('details')"
        >Dienstdaten</button>
        <button
          id="tab-attendance"
          type="button"
          role="tab"
          :aria-selected="tab === 'attendance'"
          :tabindex="tab === 'attendance' ? 0 : -1"
          aria-controls="panel-attendance"
          @click="setTab('attendance')"
        >Anwesenheit</button>
      </div>

      <div v-show="tab === 'details'" id="panel-details" :role="isEdit ? 'tabpanel' : undefined" :aria-labelledby="isEdit ? 'tab-details' : undefined">
        <ServiceForm
          :initial-data="servicebookStore.currentService"
          :loading="saving"
          :submit-label="isEdit ? 'Änderungen speichern' : 'Dienst anlegen'"
          @submit="handleSubmit"
          @cancel="handleBack"
        />
      </div>

      <div
        v-if="isEdit && serviceId !== null && service"
        v-show="tab === 'attendance'"
        id="panel-attendance"
        role="tabpanel"
        aria-labelledby="tab-attendance"
      >
        <AttendanceManager :service-id="serviceId" />
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import DeleteServiceButton from '@/components/servicebook/molecules/DeleteServiceButton.vue'
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import StateView from '@/components/common/StateView.vue'
import ServiceForm from '@/components/servicebook/organisms/ServiceForm.vue'
import AttendanceManager from '@/components/servicebook/organisms/AttendanceManager.vue'
import { useServicebookStore } from '@/stores/servicebook'
import type { ServiceFormData } from '@/types/servicebook'
import { getApiErrorMessage } from '@/utils/apiError'

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
const tab = ref<'details' | 'attendance'>(route.query.tab === 'attendance' ? 'attendance' : 'details')
const service = computed(() => (isEdit.value ? servicebookStore.currentService : null))

const dateLine = computed(() => {
  if (!service.value) return ''
  const start = new Date(service.value.start)
  const end = new Date(service.value.end)
  const time = (d: Date) => d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
  return `${start.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', year: 'numeric' })} · ${time(start)}–${time(end)}`
})

function switchByKey() {
  setTab(tab.value === 'details' ? 'attendance' : 'details')
  document.getElementById(`tab-${tab.value}`)?.focus()
}

function setTab(next: 'details' | 'attendance') {
  tab.value = next
  router.replace({ query: { ...route.query, tab: next === 'details' ? undefined : next } })
}

onMounted(async () => {
  if (isEdit.value && serviceId.value) {
    loading.value = true
    try {
      await servicebookStore.fetchService(serviceId.value)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden des Dienstes')
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
  } catch (err) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: getApiErrorMessage(err, 'Fehler beim Speichern des Dienstes'),
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
.service-edit {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 960px;
  margin: 0 auto;
}

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.breadcrumb a {
  color: var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.breadcrumb i {
  font-size: 0.75rem;
}

.edit-head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.edit-head__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}

.edit-head h1 {
  margin: 0;
  font-size: var(--jf-text-2xl);
  line-height: var(--jf-leading-tight);
  letter-spacing: -0.015em;
}

.edit-head__meta {
  margin: 0;
  color: var(--jf-color-text-muted);
}

.segmented {
  display: flex;
  gap: 4px;
  max-width: 420px;
  padding: 4px;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-border);
}

.segmented button {
  flex: 1;
  min-height: 40px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--jf-color-text-muted);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
}

.segmented button[aria-selected='true'] {
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  box-shadow: 0 1px 2px rgba(23, 32, 51, 0.12);
}

@media (max-width: 767px) {
  .edit-head h1 {
    font-size: var(--jf-text-xl);
  }

  .segmented {
    max-width: none;
  }
}
</style>
