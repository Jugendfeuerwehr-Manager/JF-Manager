<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import { qualificationsApi } from '@/api/qualifications'
import AttachmentsSection from '@/components/qualifications/organisms/AttachmentsSection.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import Button from 'primevue/button'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { getApiErrorMessage } from '@/utils/apiError'
import { formatDate, qualificationStatus } from '@/components/qualifications/utils/qualificationStatus'
import type { Qualification } from '@/types/qualifications'

const route = useRoute()
const router = useRouter()
const qualificationsStore = useQualificationsStore()
const confirm = useConfirm()
const toast = useToast()

const qualificationId = computed(() => Number(route.params.id))
const qualification = computed(() => qualificationsStore.currentQualification)
const loading = computed(() => qualificationsStore.loadingDetail)
const loadError = ref<string | null>(null)
const status = computed(() => (qualification.value ? qualificationStatus(qualification.value) : null))

// Verlauf: all records of the same type for the same person, newest first.
const history = ref<Qualification[]>([])
const historyFailed = ref(false)
const latest = computed(() => history.value[0] ?? null)
const supersededBy = computed(() =>
  latest.value && qualification.value && latest.value.id !== qualification.value.id ? latest.value : null
)
const canRenew = computed(() => Boolean(qualification.value?.date_expires) && !supersededBy.value)

async function loadHistory() {
  const current = qualification.value
  history.value = []
  historyFailed.value = false
  if (!current) return
  try {
    const response = await qualificationsApi.list({
      type: current.type,
      ...(current.member ? { member: current.member } : { user: current.user ?? undefined }),
      ordering: '-date_acquired',
      page_size: 50
    })
    history.value = response.data.results
  } catch {
    historyFailed.value = true
  }
}

async function loadQualification() {
  if (!qualificationId.value) {
    loadError.value = 'Ungültige Qualifikation.'
    return
  }
  loadError.value = null
  try {
    await qualificationsStore.fetchQualification(qualificationId.value)
    await loadHistory()
  } catch (error) {
    loadError.value = getApiErrorMessage(error, 'Die Qualifikation konnte nicht geladen werden.')
  }
}

function navigateBack() {
  router.push('/qualifications')
}

function navigateToEdit() {
  router.push(`/qualifications/${qualificationId.value}/edit`)
}

function renew() {
  router.push({ path: '/qualifications/create', query: { renew: String(qualificationId.value) } })
}

function handleDelete() {
  if (!qualificationId.value) return

  confirm.require({
    message: 'Soll diese Qualifikation dauerhaft gelöscht werden?',
    header: 'Qualifikation löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await qualificationsStore.deleteQualification(qualificationId.value)
        toast.add({
          severity: 'success',
          summary: 'Qualifikation gelöscht',
          detail: 'Die Qualifikation wurde entfernt.',
          life: 3000
        })
        navigateBack()
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: getApiErrorMessage(error, 'Qualifikation konnte nicht gelöscht werden.'),
          life: 4000
        })
      }
    }
  })
}

onMounted(loadQualification)

watch(() => route.params.id, loadQualification)
</script>

<template>
  <div class="qualification-detail">
    <nav class="breadcrumb" aria-label="Brotkrumen">
      <router-link to="/qualifications"><i class="pi pi-arrow-left" aria-hidden="true"></i>Qualifikationen</router-link>
    </nav>

    <StateView v-if="loadError" kind="error" :message="loadError" @retry="loadQualification" />
    <StateView v-else-if="loading && !qualification" kind="loading" />

    <template v-else-if="qualification">
      <OverviewHeader :title="qualification.type_name" :subtitle="qualification.person_name">
        <template #badge>
          <StatusBadge v-if="status" v-bind="status" />
        </template>
        <template #actions>
          <Button label="Löschen" icon="pi pi-trash" severity="danger" text @click="handleDelete" />
          <Button label="Bearbeiten" icon="pi pi-pencil" :severity="canRenew ? 'secondary' : undefined" :outlined="canRenew" @click="navigateToEdit" />
          <Button v-if="canRenew" label="Verlängern" icon="pi pi-replay" @click="renew" />
        </template>
      </OverviewHeader>

      <div v-if="supersededBy" class="notice" role="status">
        <i class="pi pi-history" aria-hidden="true"></i>
        <span>
          Verlängert am {{ formatDate(supersededBy.date_acquired) }}.
          <router-link :to="`/qualifications/${supersededBy.id}`">Aktuellen Eintrag öffnen</router-link>
        </span>
      </div>

      <div class="detail-layout">
        <section class="card" aria-labelledby="facts-title">
          <h2 id="facts-title" class="card-title">Angaben</h2>
          <dl class="facts">
            <div><dt>Erworben am</dt><dd>{{ formatDate(qualification.date_acquired) }}</dd></div>
            <div><dt>Gültig bis</dt><dd>{{ qualification.date_expires ? formatDate(qualification.date_expires) : 'unbefristet' }}</dd></div>
            <div><dt>Ausgestellt von</dt><dd>{{ qualification.issued_by || '–' }}</dd></div>
            <div v-if="qualification.user_name"><dt>Benutzerkonto</dt><dd>{{ qualification.user_name }}</dd></div>
          </dl>
          <h3 class="subhead">Notizen</h3>
          <p v-if="qualification.note" class="note">{{ qualification.note }}</p>
          <p v-else class="muted">Keine Notizen hinterlegt.</p>
        </section>

        <section class="card" aria-labelledby="history-title">
          <h2 id="history-title" class="card-title">Verlauf</h2>
          <StateView v-if="historyFailed" kind="error" title="Verlauf nicht geladen" message="" @retry="loadHistory" />
          <ol v-else class="history">
            <li v-for="entry in history" :key="entry.id" :aria-current="entry.id === qualification.id ? 'true' : undefined">
              <router-link :to="`/qualifications/${entry.id}`" class="history__link">
                <span class="history__dates">
                  <strong>{{ formatDate(entry.date_acquired) }}</strong>
                  <span>bis {{ entry.date_expires ? formatDate(entry.date_expires) : 'unbefristet' }}</span>
                </span>
                <StatusBadge v-if="entry.id !== latest?.id" label="Verlängert" severity="neutral" icon="pi pi-history" />
                <StatusBadge v-else v-bind="qualificationStatus(entry)" />
              </router-link>
            </li>
          </ol>
        </section>
      </div>

      <AttachmentsSection
        :source-id="qualification.id"
        source-type="qualification"
        :initial-attachments="qualification.attachments || []"
      />
    </template>
  </div>
</template>

<style scoped>
.qualification-detail {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 1040px;
}
.qualification-detail :deep(.overview-header) { margin-bottom: 0; }

.breadcrumb a {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  min-height: var(--jf-touch-target);
  color: var(--jf-color-primary);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.notice {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
}

.detail-layout {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--jf-space-2);
}

.card {
  padding: var(--jf-space-3);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-sm);
}
.card-title { margin: 0 0 var(--jf-space-2); font-size: var(--jf-text-lg); }
.subhead { margin: var(--jf-space-3) 0 var(--jf-space-1); font-size: var(--jf-text-md); }

.facts { margin: 0; display: grid; gap: var(--jf-space-1-5); }
.facts div { display: flex; justify-content: space-between; gap: var(--jf-space-2); padding-bottom: var(--jf-space-1); border-bottom: 1px solid var(--jf-color-border); }
.facts dt { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.facts dd { margin: 0; font-weight: var(--jf-weight-semibold); text-align: right; }
.note { margin: 0; white-space: pre-line; }
.muted { margin: 0; color: var(--jf-color-text-muted); }

.history { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: var(--jf-space-1); }
.history__link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5);
  min-height: var(--jf-touch-target);
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  text-decoration: none;
}
.history__link:hover { background: var(--p-content-hover-background); }
.history li[aria-current='true'] .history__link { border-color: var(--jf-color-primary); background: var(--jf-color-selected); }
.history__dates { display: flex; flex-direction: column; font-size: var(--jf-text-sm); }
.history__dates span { color: var(--jf-color-text-muted); }
</style>
