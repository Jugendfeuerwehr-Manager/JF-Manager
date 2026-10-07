<template>
  <div class="session-form">
    <div class="fields">
      <div class="field">
        <label for="training-title">Titel *</label>
        <InputText id="training-title" v-model="form.title" :invalid="!form.title && submitted" class="w-full" />
      </div>

      <div class="field-row">
        <div class="field">
          <label for="training-date">Datum *</label>
          <DatePicker input-id="training-date" v-model="formDate" date-format="dd.mm.yy" :update-model-type="'date'" class="w-full" show-icon />
        </div>
        <div class="field">
          <label for="training-start">Beginn</label>
          <InputText id="training-start" v-model="form.start_time" placeholder="08:00" class="w-full" />
        </div>
        <div class="field">
          <label for="training-end">Ende</label>
          <InputText id="training-end" v-model="form.end_time" placeholder="10:00" class="w-full" />
        </div>
      </div>

      <div class="field">
        <label for="training-location">Ort</label>
        <InputText id="training-location" v-model="form.location" class="w-full" />
      </div>

      <div class="field">
        <label for="training-description">Beschreibung</label>
        <Textarea id="training-description" v-model="form.description" rows="2" class="w-full" />
      </div>

      <div class="field">
        <label>Gruppen</label>
        <MultiSelect
          v-model="form.group_ids"
          :options="groups"
          option-label="name"
          option-value="id"
          placeholder="Alle Gruppen"
          class="w-full"
        />
      </div>

      <Divider />

      <!-- Recurrence -->
      <div class="field-checkbox">
        <Checkbox v-model="hasRecurrence" input-id="has-recurrence" :binary="true" />
        <label for="has-recurrence">Wiederkehrende Übung</label>
      </div>

      <template v-if="hasRecurrence">
        <div class="field-row">
          <div class="field">
            <label>Häufigkeit</label>
            <Select
              v-model="recurrenceRule.frequency"
              :options="frequencyOptions"
              option-label="label"
              option-value="value"
              class="w-full"
            />
          </div>
          <div class="field">
            <label>Enddatum</label>
            <DatePicker v-model="recurrenceEndDate" date-format="dd.mm.yy" :update-model-type="'date'" class="w-full" show-icon />
          </div>
        </div>
      </template>

      <div class="field">
        <label for="training-notes">Notizen (intern)</label>
        <Textarea id="training-notes" v-model="form.notes" rows="2" class="w-full" />
      </div>
    </div>

    <p v-if="error" role="alert">{{ error }}</p>
    <div class="form-actions">
      <Button label="Abbrechen" severity="secondary" outlined @click="emit('cancel')" />
      <Button
        :label="draftOnly ? 'Übernehmen' : initialData ? 'Speichern' : 'Erstellen'"
        icon="pi pi-check"
        :loading="saving"
        @click="submit"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import DatePicker from 'primevue/datepicker'
import { useDepartmentsStore } from '@/stores/departments'
import { useTrainingStore } from '@/stores/training'
import type { TrainingSessionDetail, TrainingSessionCreate, RecurrenceRule } from '@/types/training'
import apiClient from '@/api'
import { useClientConfiguration } from '@/composables/useClientConfiguration'
const { configuration, refresh: refreshDefaults } = useClientConfiguration()

interface SessionFormData {
  title: string
  description: string
  date: string
  start_time: string
  end_time: string
  location: string
  notes: string
  group_ids: number[]
  recurrence_rule: RecurrenceRule | null
}

interface Props {
  /** Provide TrainingSessionDetail when editing an existing session */
  initialData?: TrainingSessionDetail | null
  draftOnly?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  success: [sessionId: number]
  draft: [data: TrainingSessionCreate, choices: { id: number; name: string }[]]
  cancel: []
}>()

const trainingStore = useTrainingStore()
const saving = ref(false)
const submitted = ref(false)
const error = ref('')
const groups = ref<{ id: number; name: string }[]>([])

const hasRecurrence = ref(false)

const form = ref<SessionFormData>({
  title: '',
  description: '',
  date: '',
  start_time: configuration.training_start_time,
  end_time: configuration.training_end_time,
  location: '',
  notes: '',
  group_ids: [],
  recurrence_rule: null,
})

const formDate = ref<Date | null>(null)
const recurrenceEndDate = ref<Date | null>(null)

const recurrenceRule = ref<RecurrenceRule>({
  frequency: 'WEEKLY',
  end_date: '',
})

const frequencyOptions = [
  { label: 'Wöchentlich', value: 'WEEKLY' },
  { label: 'Zweiwöchentlich', value: 'BIWEEKLY' },
  { label: 'Monatlich', value: 'MONTHLY' },
]

onMounted(async () => {
  if (props.initialData) populateForm(props.initialData)
  else {
    const initialStart = form.value.start_time
    const initialEnd = form.value.end_time
    void refreshDefaults().then(() => {
      if (props.initialData) return
      if (form.value.start_time === initialStart) form.value.start_time = configuration.training_start_time
      if (form.value.end_time === initialEnd) form.value.end_time = configuration.training_end_time
    }).catch(() => { /* Offline creation retains safe defaults. */ })
  }
  const department = props.initialData?.id ? props.initialData.department : useDepartmentsStore().activeDepartmentId
  try {
    const choices: { id: number; name: string }[] = []
    let offset = 0
    while (true) {
      const res = await apiClient.get<{ results: { id: number; name: string; department: number | null }[]; count: number }>('/groups/', { params: { department, limit: 200, offset } })
      choices.push(...res.data.results.filter((group) => group.department === department))
      offset += res.data.results.length
      if (!res.data.results.length || offset >= res.data.count) break
    }
    groups.value = choices
  } catch { error.value = 'Gruppen konnten nicht geladen werden. Eingaben bleiben erhalten.' }
})

watch(() => props.initialData, (data) => { if (data) populateForm(data) })

function toLocalIsoDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseIsoDateToLocalDate(isoDate: string): Date | null {
  const [yearStr, monthStr, dayStr] = isoDate.split('-')
  const year = Number(yearStr)
  const month = Number(monthStr)
  const day = Number(dayStr)

  if (!year || !month || !day) {
    return null
  }

  return new Date(year, month - 1, day)
}

function populateForm(data: Partial<TrainingSessionDetail>) {
  form.value = {
    title: data.title ?? '',
    description: data.description ?? '',
    date: data.date ?? '',
    start_time: data.start_time ?? '18:00',
    end_time: data.end_time ?? '20:00',
    location: data.location ?? '',
    notes: data.notes ?? '',
    group_ids: data.groups?.map((g) => g.id) ?? [],
    recurrence_rule: data.recurrence_rule ?? null,
  }
  hasRecurrence.value = !!data.recurrence_rule
  recurrenceRule.value = data.recurrence_rule ? { ...data.recurrence_rule } : { frequency: 'WEEKLY', end_date: '' }
  recurrenceEndDate.value = data.recurrence_rule?.end_date ? parseIsoDateToLocalDate(data.recurrence_rule.end_date) : null
  formDate.value = data.date ? parseIsoDateToLocalDate(data.date) : null
}

// Sync date picker to form
watch(formDate, (d) => {
  form.value.date = d ? toLocalIsoDate(d) : ''
})
watch(recurrenceEndDate, (d) => {
  recurrenceRule.value.end_date = d ? toLocalIsoDate(d) : ''
})

async function submit() {
  submitted.value = true
  if (!form.value.title.trim() || !form.value.date) return

  error.value = ''
  if (!/^\d{2}:\d{2}(:\d{2})?$/.test(form.value.start_time) || !/^\d{2}:\d{2}(:\d{2})?$/.test(form.value.end_time) || form.value.end_time <= form.value.start_time) {
    error.value = 'Beginn und Ende im Format HH:MM angeben. Das Ende muss am selben Tag nach dem Beginn liegen.'
    return
  }
  if (!props.draftOnly && props.initialData?.requires_service_confirmation && !window.confirm('Dokumentierten oder begonnenen Dienst ausdrücklich ändern? Anwesenheiten bleiben erhalten.')) return
  saving.value = true
  try {
    const payload: TrainingSessionCreate = {
      ...form.value,
      recurrence_rule: hasRecurrence.value ? recurrenceRule.value : null,
    }

    if (props.draftOnly) {
      emit('draft', payload, groups.value)
    } else if (props.initialData?.id) {
      payload.confirm_service_change = !!props.initialData.requires_service_confirmation
      await trainingStore.updateSession(props.initialData.id, payload)
      emit('success', props.initialData.id)
    } else {
      const session = await trainingStore.createSession(payload)
      if (session) emit('success', session.id)
    }
  } catch (e: unknown) {
    const response = (e as { response?: { data?: unknown } }).response
    const messages = (value: unknown): string[] => typeof value === 'string' ? [value] : value && typeof value === 'object' ? Object.values(value).flatMap(messages) : []
    error.value = messages(response?.data).join(' ') || 'Nicht gespeichert. Verbindung und Berechtigung prüfen und erneut versuchen.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.session-form { display: flex; flex-direction: column; gap: 1rem; }
.fields { display: flex; flex-direction: column; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: 0.35rem; }
.field-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 1rem; }
.field label { font-size: 0.875rem; font-weight: 500; color: var(--text-color-secondary); }
.field-checkbox { display: flex; align-items: center; gap: 0.5rem; }
.field-checkbox label { font-size: 0.875rem; margin: 0; }

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}
@media (max-width: 640px) { .field-row { grid-template-columns: 1fr; } }
</style>
