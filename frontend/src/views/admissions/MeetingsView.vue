<template>
  <div class="adm-page">
    <header class="adm-page__head">
      <div>
        <h1>Sitzungen</h1>
        <p class="adm-page__lead">Beschlüsse des Gremiums über mehrere Anträge gesammelt erfassen.</p>
      </div>
      <AdmButton v-if="canCreate" variant="primary" icon="pi pi-plus" @click="createDialog?.showModal()">Sitzung anlegen</AdmButton>
    </header>

    <p v-if="store.error" class="adm-page__error" role="alert">{{ store.error }}</p>

    <div class="adm-table-wrap">
      <table class="adm-table">
        <caption class="sr-only">Sitzungen</caption>
        <thead>
          <tr>
            <th scope="col">Datum</th>
            <th scope="col">Gremium</th>
            <th scope="col">Protokoll</th>
            <th scope="col">Beschlüsse</th>
            <th scope="col"><span class="sr-only">Aktionen</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!store.meetings.length">
            <td colspan="5" class="adm-table__empty">{{ store.loading ? 'Lade …' : 'Noch keine Sitzung.' }}</td>
          </tr>
          <tr v-for="meeting in store.meetings" :key="meeting.id">
            <td>{{ new Date(`${meeting.date}T00:00:00`).toLocaleDateString('de-DE') }}</td>
            <td>{{ meeting.body }}</td>
            <td>{{ meeting.protocol_ref || '–' }}</td>
            <td>{{ meeting.decision_count }}</td>
            <td class="adm-table__actions">
              <AdmButton v-if="canDecide" icon="pi pi-check-square" @click="openDecide(meeting)">Beschließen</AdmButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <dialog ref="createDialog" class="adm-dialog" aria-labelledby="meeting-title">
      <form class="adm-dialog__body" @submit.prevent="createMeeting">
        <h2 id="meeting-title">Sitzung anlegen</h2>
        <AdmField input-id="m-department" label="Abteilung" required>
          <select id="m-department" v-model.number="draft.department" class="adm-input" required>
            <option v-for="department in departments.departments" :key="department.id" :value="department.id">{{ department.name }}</option>
          </select>
        </AdmField>
        <AdmField input-id="m-body" label="Gremium" required>
          <input id="m-body" v-model="draft.body" class="adm-input" required maxlength="100" />
        </AdmField>
        <AdmField input-id="m-date" label="Datum" required>
          <input id="m-date" v-model="draft.date" type="date" class="adm-input" required />
        </AdmField>
        <AdmField input-id="m-protocol" label="Protokoll (Verweis)">
          <input id="m-protocol" v-model="draft.protocol_ref" class="adm-input" maxlength="200" />
        </AdmField>
        <div class="adm-dialog__actions">
          <AdmButton variant="ghost" @click="createDialog?.close()">Abbrechen</AdmButton>
          <AdmButton variant="primary" type="submit" icon="pi pi-check" :loading="store.saving">Anlegen</AdmButton>
        </div>
      </form>
    </dialog>

    <dialog ref="decideDialog" class="adm-dialog" aria-labelledby="decide-title">
      <form v-if="selected" class="adm-dialog__body" @submit.prevent="decide">
        <h2 id="decide-title">{{ selected.body }} am {{ new Date(`${selected.date}T00:00:00`).toLocaleDateString('de-DE') }}</h2>
        <fieldset class="meeting__list">
          <legend>Offene Anträge</legend>
          <p v-if="!openApplications.length" class="adm-page__lead">Keine offenen Anträge in dieser Abteilung.</p>
          <label v-for="application in openApplications" :key="application.id" class="meeting__choice">
            <input v-model="chosen" type="checkbox" class="adm-check" :value="application.id" />
            {{ application.applicant_name }} ({{ new Date(application.submitted_at).toLocaleDateString('de-DE') }})
          </label>
        </fieldset>
        <AdmField input-id="b-outcome" label="Ergebnis für alle gewählten">
          <select id="b-outcome" v-model="outcome" class="adm-input">
            <option value="approved">Aufnahme angenommen</option>
            <option value="deferred">Zurückgestellt</option>
            <option value="rejected">Abgelehnt</option>
          </select>
        </AdmField>
        <div class="adm-dialog__actions">
          <AdmButton variant="ghost" @click="decideDialog?.close()">Abbrechen</AdmButton>
          <AdmButton variant="primary" type="submit" icon="pi pi-check" :loading="store.saving" :disabled="!chosen.length">
            {{ chosen.length }} Beschlüsse versiegeln
          </AdmButton>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import AdmField from '@/components/admissions/atoms/AdmField.vue'
import '@/components/admissions/atoms/admInput.css'
import '@/components/admissions/atoms/admPage.css'
import { useAdmissionsStore } from '@/stores/admissions'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import type { CommitteeMeeting, DecisionOutcome } from '@/types/admissions'

const store = useAdmissionsStore()
const auth = useAuthStore()
const departments = useDepartmentsStore()

const createDialog = ref<HTMLDialogElement | null>(null)
const decideDialog = ref<HTMLDialogElement | null>(null)
const selected = ref<CommitteeMeeting | null>(null)
const chosen = ref<number[]>([])
const outcome = ref<DecisionOutcome>('approved')
const draft = reactive({
  department: departments.activeDepartmentId ?? departments.departments[0]?.id ?? 0,
  body: 'Jugendausschuss',
  date: new Date().toISOString().slice(0, 10),
  protocol_ref: '',
  note: ''
})

const canCreate = computed(() => auth.hasPerm('admissions.add_committeemeeting'))
const canDecide = computed(() => auth.hasPerm('admissions.record_decision'))
const openApplications = computed(() =>
  store.applications.filter(
    (application) => application.department === selected.value?.department && ['submitted', 'deferred'].includes(application.status)
  )
)

async function createMeeting() {
  try {
    await store.createMeeting({ ...draft })
    createDialog.value?.close()
  } catch {
    // store.error is shown on the page
  }
}

async function openDecide(meeting: CommitteeMeeting) {
  selected.value = meeting
  chosen.value = []
  await store.fetchApplications()
  decideDialog.value?.showModal()
}

async function decide() {
  if (!selected.value) return
  try {
    await store.decideInMeeting(selected.value.id, { outcome: outcome.value, applications: chosen.value })
    decideDialog.value?.close()
  } catch {
    // store.error is shown on the page
  }
}

onMounted(() => store.fetchMeetings())
</script>

<style scoped>
.meeting__list {
  margin: 0;
  padding: var(--jf-space-1);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  max-height: 16rem;
  overflow-y: auto;
}

.meeting__choice {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
}
</style>
