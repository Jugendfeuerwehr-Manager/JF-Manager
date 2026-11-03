<template>
  <form class="settings" @submit.prevent="save">
    <h2>Einstellungen</h2>
    <AdmField input-id="set-title" label="Titel" required>
      <input id="set-title" v-model="local.title" class="adm-input" required maxlength="200" :disabled="!canEdit" />
    </AdmField>
    <AdmField input-id="set-intro" label="Einleitung" hint="Wird oberhalb des Formulars angezeigt.">
      <textarea id="set-intro" v-model="local.intro" class="adm-input" :disabled="!canEdit"></textarea>
    </AdmField>
    <AdmField input-id="set-signature" label="Unterschrift">
      <select id="set-signature" v-model="local.signature_mode" class="adm-input" :disabled="!canEdit">
        <option value="both">Digital unterschreiben und zusätzlich ausdrucken</option>
        <option value="digital">Nur digital unterschreiben</option>
        <option value="print">Ausdrucken und auf Papier unterschreiben</option>
      </select>
    </AdmField>
    <AdmField input-id="set-body" label="Entscheidungsgremium" hint="Wer über die Aufnahme beschließt, z. B. Jugendausschuss.">
      <input id="set-body" v-model="local.decision_body" class="adm-input" maxlength="100" :disabled="!canEdit" />
    </AdmField>
    <AdmField input-id="set-status" label="Status nach Übernahme" hint="Nur Stufen der Kategorien Antrag, Probezeit oder Aktiv.">
      <select id="set-status" v-model="local.initial_status" class="adm-input" :disabled="!canEdit">
        <option :value="null">Kein Status</option>
        <option v-for="status in statusOptions" :key="status.id" :value="status.id">{{ status.name }}</option>
      </select>
    </AdmField>
    <label class="settings__check">
      <input v-model="local.is_active" type="checkbox" class="adm-check" :disabled="!canEdit" />
      Für neue Voucher verfügbar
    </label>
    <div>
      <AdmButton variant="primary" type="submit" icon="pi pi-check" :disabled="!canEdit">Einstellungen speichern</AdmButton>
    </div>
  </form>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import AdmButton from '../atoms/AdmButton.vue'
import AdmField from '../atoms/AdmField.vue'
import { useMembersStore } from '@/stores/members'
import type { AdmissionForm, AdmissionFormUpdate } from '@/types/admissions'
import '../atoms/admInput.css'

interface Props {
  form: AdmissionForm
  canEdit: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'save', data: AdmissionFormUpdate): void }>()
const membersStore = useMembersStore()

const local = reactive<Required<Omit<AdmissionFormUpdate, 'draft_schema'>>>({
  title: '',
  intro: '',
  signature_mode: 'both',
  decision_body: '',
  initial_status: null,
  is_active: true
})

const statusOptions = computed(() =>
  membersStore.statuses.filter(
    (status) =>
      ['applicant', 'trial', 'active'].includes(status.category) &&
      (status.department === null || status.department === props.form.department)
  )
)

function load(form: AdmissionForm) {
  Object.assign(local, {
    title: form.title,
    intro: form.intro,
    signature_mode: form.signature_mode,
    decision_body: form.decision_body,
    initial_status: form.initial_status,
    is_active: form.is_active
  })
}

function save() {
  emit('save', { ...local })
}

watch(() => props.form, load, { immediate: true })
onMounted(() => {
  if (!membersStore.statuses.length) membersStore.fetchStatuses()
})
</script>

<style scoped>
.settings {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 40rem;
}

.settings h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
}

.settings__check {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
}
</style>
