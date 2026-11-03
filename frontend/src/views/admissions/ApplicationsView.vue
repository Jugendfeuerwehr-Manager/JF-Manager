<template>
  <div class="adm-page">
    <header class="adm-page__head">
      <div>
        <h1>Aufnahmeanträge</h1>
        <p class="adm-page__lead">Eingegangene Anträge prüfen, beschließen lassen und übernehmen.</p>
      </div>
    </header>

    <div class="adm-filters" role="group" aria-label="Nach Status filtern">
      <AdmButton
        v-for="filter in FILTERS"
        :key="filter.value"
        :aria-pressed="status === filter.value"
        @click="setStatus(filter.value)"
      >
        {{ filter.label }}
      </AdmButton>
    </div>

    <p v-if="store.error" class="adm-page__error" role="alert">{{ store.error }}</p>

    <div class="adm-table-wrap">
      <table class="adm-table">
        <caption class="sr-only">Aufnahmeanträge</caption>
        <thead>
          <tr>
            <th scope="col">Antragsteller*in</th>
            <th scope="col">Eingereicht</th>
            <th scope="col">Formular</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!store.applications.length">
            <td colspan="4" class="adm-table__empty">{{ store.loading ? 'Lade …' : 'Keine Anträge in dieser Ansicht.' }}</td>
          </tr>
          <tr v-for="application in store.applications" :key="application.id">
            <td>
              <RouterLink :to="{ name: 'admission-application', params: { id: application.id } }">{{ application.applicant_name }}</RouterLink>
            </td>
            <td>{{ new Date(application.submitted_at).toLocaleDateString('de-DE') }}</td>
            <td>{{ application.form_title }} (v{{ application.form_version_number }})</td>
            <td><span class="adm-badge" :data-state="application.status">{{ application.status_label }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import '@/components/admissions/atoms/admPage.css'
import { useAdmissionsStore } from '@/stores/admissions'
import type { ApplicationStatus } from '@/types/admissions'

const FILTERS: { value: ApplicationStatus | ''; label: string }[] = [
  { value: 'submitted', label: 'Eingegangen' },
  { value: 'deferred', label: 'Zurückgestellt' },
  { value: 'approved', label: 'Angenommen' },
  { value: 'taken_over', label: 'Übernommen' },
  { value: 'rejected', label: 'Abgelehnt' },
  { value: '', label: 'Alle' }
]

const store = useAdmissionsStore()
const status = ref<ApplicationStatus | ''>('submitted')

function setStatus(value: ApplicationStatus | '') {
  status.value = value
  store.fetchApplications(value ? { status: value } : undefined)
}

onMounted(() => setStatus('submitted'))
</script>
