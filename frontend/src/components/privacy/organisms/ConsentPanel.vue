<template>
  <section class="consent-panel">
    <div class="consent-panel__header">
      <h3 class="consent-panel__title">Einwilligungen</h3>
      <div class="consent-panel__actions">
        <Button
          v-if="canExport"
          label="Datenauskunft"
          icon="pi pi-download"
          size="small"
          text
          :loading="privacyStore.exporting"
          v-tooltip.bottom="'Alle gespeicherten Daten dieser Person als ZIP (Art. 15 DSGVO)'"
          @click="privacyStore.downloadSubjectAccess(subject)"
        />
        <Button
          v-if="canEdit && !formOpen"
          label="Erfassen"
          icon="pi pi-plus"
          size="small"
          text
          @click="formOpen = true"
        />
      </div>
    </div>

    <Message v-if="privacyStore.consentsError" severity="error" :closable="false">{{ privacyStore.consentsError }}</Message>

    <form v-if="formOpen" class="consent-panel__form" @submit.prevent="submit">
      <Select v-model="kind" :options="kindOptions" option-label="label" option-value="value" placeholder="Art" class="w-full" />
      <SelectButton v-model="status" :options="statusOptions" option-label="label" option-value="value" :allow-empty="false" />
      <InputText v-model="note" placeholder="Notiz, z. B. „Formular vom 01.10.“" maxlength="300" class="w-full" />
      <div class="consent-panel__form-actions">
        <Button type="button" label="Abbrechen" severity="secondary" text @click="formOpen = false" />
        <Button type="submit" label="Speichern" :disabled="!kind" :loading="privacyStore.consentsSaving" />
      </div>
    </form>

    <p v-if="!privacyStore.consentsLoading && !current.length" class="consent-panel__empty">Keine Einwilligungen erfasst.</p>
    <ul v-else class="consent-panel__list">
      <li v-for="record in current" :key="record.kind">
        <i :class="record.status === 'granted' ? 'pi pi-check-circle consent-panel__ok' : 'pi pi-times-circle consent-panel__no'" />
        <div class="consent-panel__entry">
          <div>{{ record.kind_label }}</div>
          <small>
            {{ record.status_label }} am {{ formatDate(record.recorded_at) }} · {{ record.source_label }}
            <template v-if="record.recorded_by_name"> ({{ record.recorded_by_name }})</template>
            <template v-if="record.text_version"> · {{ record.text_version }}</template>
            <template v-if="record.note"> · {{ record.note }}</template>
          </small>
          <!-- Withdrawing is a new record, but it is offered on the consent it ends. -->
          <div v-if="canEdit && record.status === 'granted'" class="consent-panel__withdraw">
            <template v-if="withdrawing === record.kind">
              <InputText v-model="withdrawNote" placeholder="Notiz, z. B. „Anruf am 02.11.“" maxlength="300" size="small" class="w-full" />
              <Button label="Widerruf speichern" severity="danger" size="small" :loading="privacyStore.consentsSaving" @click="withdraw(record)" />
              <Button label="Abbrechen" severity="secondary" size="small" text @click="withdrawing = null" />
            </template>
            <Button v-else label="Widerrufen" icon="pi pi-undo" size="small" text @click="startWithdraw(record)" />
          </div>
        </div>
      </li>
    </ul>

    <Button
      v-if="privacyStore.consents.length > current.length"
      :label="historyOpen ? 'Verlauf ausblenden' : `Verlauf (${privacyStore.consents.length} Einträge)`"
      size="small"
      text
      @click="historyOpen = !historyOpen"
    />
    <ul v-if="historyOpen" class="consent-panel__history">
      <li v-for="record in privacyStore.consents" :key="record.id">
        {{ formatDate(record.recorded_at) }}: {{ record.kind_label }} – {{ record.status_label }}
        ({{ record.source_label }}<template v-if="record.recorded_by_name">, {{ record.recorded_by_name }}</template>)
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import { usePrivacyStore } from '@/stores/privacy'
import type { ConsentRecord, ConsentStatus, ConsentSubject } from '@/types/privacy'

interface Props {
  subject: ConsentSubject
  canEdit: boolean
  /** Offers the Art. 15 data copy; the server checks the export right again. */
  canExport?: boolean
}

const props = withDefaults(defineProps<Props>(), { canExport: false })
const privacyStore = usePrivacyStore()

const formOpen = ref(false)
const historyOpen = ref(false)
const kind = ref<string | null>(null)
const status = ref<ConsentStatus>('granted')
const note = ref('')
const statusOptions = [
  { label: 'Erteilt', value: 'granted' },
  { label: 'Widerrufen', value: 'withdrawn' },
]
// Active kinds from the privacy settings; old records keep their label from the server.
const kindOptions = computed(() =>
  privacyStore.consentKinds.filter(kind => kind.active).map(kind => ({ value: kind.slug, label: kind.label }))
)
const withdrawing = ref<string | null>(null)
const withdrawNote = ref('')

if (!privacyStore.consentKinds.length) void privacyStore.fetchConsentKinds()

function startWithdraw(record: ConsentRecord) {
  withdrawNote.value = ''
  withdrawing.value = record.kind
}

async function withdraw(record: ConsentRecord) {
  const ok = await privacyStore.recordConsent(props.subject, {
    kind: record.kind,
    status: 'withdrawn',
    note: withdrawNote.value || 'Widerruf',
  })
  if (ok) withdrawing.value = null
}

/** Newest record per kind (the list arrives newest first). */
const current = computed(() => {
  const seen = new Map<string, ConsentRecord>()
  for (const record of privacyStore.consents) if (!seen.has(record.kind)) seen.set(record.kind, record)
  return [...seen.values()]
})

watch(() => [props.subject.field, props.subject.id], () => {
  void privacyStore.fetchConsents(props.subject)
}, { immediate: true })

function formatDate(value: string) {
  return new Date(value).toLocaleDateString('de-DE')
}

async function submit() {
  if (!kind.value) return
  const ok = await privacyStore.recordConsent(props.subject, { kind: kind.value, status: status.value, note: note.value })
  if (ok) {
    formOpen.value = false
    kind.value = null
    status.value = 'granted'
    note.value = ''
  }
}
</script>

<style scoped>
.consent-panel { display: flex; flex-direction: column; gap: .75rem; }
.consent-panel__header { display: flex; align-items: center; justify-content: space-between; }
.consent-panel__title { margin: 0; font-size: 1rem; }
.consent-panel__actions { display: flex; gap: .25rem; }
.consent-panel__form { display: flex; flex-direction: column; gap: .5rem; }
.consent-panel__form-actions { display: flex; justify-content: flex-end; gap: .5rem; }
.consent-panel__empty { color: var(--text-color-secondary); margin: 0; }
.consent-panel__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: .5rem; }
.consent-panel__list li { display: flex; gap: .5rem; align-items: flex-start; }
.consent-panel__list small { color: var(--text-color-secondary); }
.consent-panel__ok { color: var(--p-green-600); margin-top: .2rem; }
.consent-panel__no { color: var(--p-red-600); margin-top: .2rem; }
.consent-panel__entry { display: flex; flex-direction: column; gap: .15rem; min-width: 0; flex: 1; }
.consent-panel__withdraw { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem; margin-top: .15rem; }
.consent-panel__history { margin: 0; padding-left: 1.25rem; font-size: .85rem; color: var(--text-color-secondary); }
</style>
