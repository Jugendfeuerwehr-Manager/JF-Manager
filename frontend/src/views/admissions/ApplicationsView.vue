<template>
  <div class="adm-page">
    <header class="adm-page__head">
      <div>
        <h1>Aufnahmeanträge</h1>
        <p class="adm-page__lead">
          Jeder Antrag durchläuft dieselben Schritte: eingehen, beschließen, übernehmen. Der nächste Schritt ist immer ein
          Knopf im Antrag.
        </p>
      </div>
      <div class="pipeline__actions">
        <RouterLink :to="{ name: 'admission-meetings' }" class="pipeline__action">Sitzungen</RouterLink>
        <RouterLink :to="{ name: 'admission-vouchers' }" class="pipeline__action pipeline__action--primary">Voucher erstellen</RouterLink>
      </div>
    </header>

    <p v-if="store.error" class="adm-page__error" role="alert">{{ store.error }}</p>

    <div v-if="waiting.length" class="pipeline__banner">
      <strong v-if="nextMeeting">Nächste Sitzung: {{ nextMeeting.body }}, {{ formatDate(nextMeeting.date) }}</strong>
      <strong v-else>Keine Sitzung geplant</strong>
      <span>{{ waiting.length }} {{ waiting.length === 1 ? 'Antrag wartet' : 'Anträge warten' }} auf einen Beschluss.</span>
      <RouterLink :to="{ name: 'admission-meetings' }" class="pipeline__banner-link">
        {{ nextMeeting ? 'Sammelbeschluss vorbereiten' : 'Sitzung anlegen' }} →
      </RouterLink>
    </div>

    <p v-if="store.loading && !store.applications.length" class="pipeline__state">Lade Anträge …</p>

    <div v-else class="pipeline">
      <section v-for="(lane, index) in lanes" :key="lane.key" class="pipeline__lane" :aria-labelledby="`lane-${lane.key}`">
        <h2 :id="`lane-${lane.key}`" class="pipeline__lane-head">
          <span>{{ index + 1 }} · {{ lane.title }}</span>
          <span class="pipeline__lane-count">{{ lane.items.length }}</span>
        </h2>
        <p v-if="!lane.items.length" class="pipeline__empty">{{ lane.empty }}</p>
        <RouterLink
          v-for="application in lane.items.slice(0, lane.limit)"
          :key="application.id"
          :to="{ name: 'admission-application', params: { id: application.id } }"
          class="pipeline__card"
        >
          <strong>{{ application.applicant_name }}</strong>
          <span class="pipeline__meta">
            <span class="pipeline__tag">{{ departmentName(application.department) }}</span>
            <span>{{ lane.dateLabel }} {{ formatDate(application.submitted_at) }}</span>
          </span>
          <span v-if="lane.next" class="pipeline__next">{{ lane.next }} →</span>
        </RouterLink>
        <button
          v-if="lane.items.length > lane.limit"
          type="button"
          class="pipeline__more"
          @click="expanded = lane.key"
        >
          Alle {{ lane.items.length }} anzeigen
        </button>
      </section>
    </div>

    <details class="pipeline__closed">
      <summary>Abgeschlossen ohne Aufnahme: {{ closed.length }}</summary>
      <ul>
        <li v-for="application in closed" :key="application.id">
          <RouterLink :to="{ name: 'admission-application', params: { id: application.id } }">{{ application.applicant_name }}</RouterLink>
          · <span class="adm-badge" :data-state="application.status">{{ application.status_label }}</span>
          · {{ formatDate(application.submitted_at) }}
        </li>
      </ul>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import '@/components/admissions/atoms/admPage.css'
import { useAdmissionsStore } from '@/stores/admissions'
import { useDepartmentsStore } from '@/stores/departments'
import type { ApplicationListItem, ApplicationStatus } from '@/types/admissions'

const COLLAPSED = 5

const store = useAdmissionsStore()
const departments = useDepartmentsStore()
const expanded = ref<string | null>(null)

const byStatus = (...statuses: ApplicationStatus[]) =>
  store.applications.filter((application) => statuses.includes(application.status))

const waiting = computed(() => byStatus('submitted', 'deferred'))
const closed = computed(() => byStatus('rejected', 'withdrawn'))
const lanes = computed(() => {
  const limit = (key: string) => (expanded.value === key ? Infinity : COLLAPSED)
  return [
    {
      key: 'submitted',
      title: 'Eingegangen',
      items: byStatus('submitted'),
      empty: 'Keine neuen Anträge.',
      dateLabel: 'eingereicht',
      next: 'Prüfen und beschließen',
      limit: limit('submitted')
    },
    {
      key: 'deferred',
      title: 'Zurückgestellt',
      items: byStatus('deferred'),
      empty: 'Nichts zurückgestellt.',
      dateLabel: 'eingereicht',
      next: 'Erneut beschließen',
      limit: limit('deferred')
    },
    {
      key: 'approved',
      title: 'Übernahme offen',
      items: byStatus('approved'),
      empty: 'Alle angenommenen Anträge sind übernommen.',
      dateLabel: 'eingereicht',
      next: 'Als Mitglied übernehmen',
      limit: limit('approved')
    },
    {
      key: 'taken_over',
      title: 'Übernommen',
      items: byStatus('taken_over'),
      empty: 'Noch niemand übernommen.',
      dateLabel: 'eingereicht',
      next: '',
      limit: limit('taken_over')
    }
  ] satisfies { key: string; title: string; items: ApplicationListItem[]; empty: string; dateLabel: string; next: string; limit: number }[]
})

const today = new Date().toISOString().slice(0, 10)
const nextMeeting = computed(
  () => [...store.meetings].filter((meeting) => meeting.date >= today).sort((a, b) => a.date.localeCompare(b.date))[0] ?? null
)

const formatDate = (iso: string) => new Date(iso.length === 10 ? `${iso}T00:00:00` : iso).toLocaleDateString('de-DE')
const departmentName = (id: number) => departments.departments.find((department) => department.id === id)?.name ?? 'Abteilung'

onMounted(() => {
  store.fetchApplications()
  store.fetchMeetings()
  if (!departments.departments.length) departments.fetchDepartments()
})
</script>

<style scoped>
.pipeline__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
}

.pipeline__action {
  display: inline-flex;
  align-items: center;
  min-height: var(--jf-touch-target, 44px);
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  font-weight: var(--jf-weight-medium);
  text-decoration: none;
}

.pipeline__action--primary {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.pipeline__banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.pipeline__banner span {
  color: var(--jf-color-text-muted);
}

.pipeline__banner-link {
  margin-left: auto;
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
}

.pipeline__state,
.pipeline__empty {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.pipeline {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
  gap: var(--jf-space-1-5);
  align-items: start;
}

.pipeline__lane {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1-5);
  border-radius: var(--jf-radius-lg);
  /* A shade darker than the page so the lanes read as columns. */
  background: color-mix(in srgb, var(--jf-color-border) 45%, var(--jf-color-ground));
}

.pipeline__lane-head {
  display: flex;
  justify-content: space-between;
  margin: 0;
  font-size: var(--jf-text-sm);
}

.pipeline__lane-count {
  color: var(--jf-color-text-muted);
}

.pipeline__card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  padding: var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  color: var(--jf-color-text);
  text-decoration: none;
}

.pipeline__card:hover {
  border-color: var(--jf-color-primary);
}

.pipeline__card:focus-visible,
.pipeline__more:focus-visible,
.pipeline__action:focus-visible {
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.pipeline__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-0-5) var(--jf-space-1);
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

.pipeline__tag {
  padding: 0 0.5rem;
  border-radius: 999px;
  background: var(--jf-color-ground);
  color: var(--jf-color-text);
}

.pipeline__next {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
}

.pipeline__more {
  min-height: var(--jf-touch-target, 44px);
  border: 0;
  background: none;
  color: var(--jf-color-primary);
  font: inherit;
  font-size: var(--jf-text-sm);
  cursor: pointer;
}

.pipeline__closed summary {
  min-height: var(--jf-touch-target, 44px);
  display: flex;
  align-items: center;
  color: var(--jf-color-text-muted);
  cursor: pointer;
}

.pipeline__closed ul {
  margin: 0;
  padding-left: 1.2rem;
}
</style>
