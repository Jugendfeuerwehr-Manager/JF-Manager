<template>
  <div class="session-form">
    <div class="fields">
      <div class="field">
        <label>Titel *</label>
        <InputText v-model="form.title" :invalid="!form.title && submitted" class="w-full" />
      </div>

      <div class="field-row">
        <div class="field">
          <label>Datum *</label>
          <DatePicker v-model="formDate" date-format="dd.mm.yy" :update-model-type="'date'" class="w-full" show-icon />
        </div>
        <div class="field">
          <label>Beginn</label>
          <InputText v-model="form.start_time" placeholder="08:00" class="w-full" />
        </div>
        <div class="field">
          <label>Ende</label>
          <InputText v-model="form.end_time" placeholder="10:00" class="w-full" />
        </div>
      </div>

      <div class="field">
        <label>Ort</label>
        <InputText v-model="form.location" class="w-full" />
      </div>

      <div class="field">
        <label>Beschreibung</label>
        <Textarea v-model="form.description" rows="2" class="w-full" />
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
        <label>Notizen (intern)</label>
        <Textarea v-model="form.notes" rows="2" class="w-full" />
      </div>
    </div>

    <div class="form-actions">
      <Button label="Abbrechen" severity="secondary" outlined @click="emit('cancel')" />
      <Button
        :label="initialData ? 'Speichern' : 'Erstellen'"
        icon="pi pi-check"
        :loading="saving"
        @click="submit"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import DatePicker from 'primevue/datepicker'
import { useTrainingStore } from '@/stores/training'
import type { TrainingSessionDetail, TrainingSessionCreate, RecurrenceRule } from '@/types/training'
import apiClient from '@/api'

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
}

const props = defineProps<Props>()
const emit = defineEmits<{
  success: [sessionId: number]
  cancel: []
}>()

const trainingStore = useTrainingStore()
const saving = ref(false)
const submitted = ref(false)
const groups = ref<{ id: number; name: string }[]>([])

const hasRecurrence = ref(false)

const form = ref<SessionFormData>({
  title: '',
  description: '',
  date: '',
  start_time: '',
  end_time: '',
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
  const res = await apiClient.get<{ results: { id: number; name: string }[] }>('/groups/')
  groups.value = res.data.results ?? res.data
  if (props.initialData) populateForm(props.initialData)
})

watch(() => props.initialData, (data) => { if (data) populateForm(data) })

function populateForm(data: Partial<TrainingSessionDetail>) {
  form.value = {
    title: data.title ?? '',
    description: data.description ?? '',
    date: data.date ?? '',
    start_time: data.start_time ?? '',
    end_time: data.end_time ?? '',
    location: data.location ?? '',
    notes: data.notes ?? '',
    group_ids: data.groups?.map((g) => g.id) ?? [],
    recurrence_rule: null,
  }
  formDate.value = data.date ? new Date(data.date) : null
}

// Sync date picker to form
watch(formDate, (d) => {
  form.value.date = d ? (d.toISOString().split('T')[0] ?? '') : ''
})
watch(recurrenceEndDate, (d) => {
  recurrenceRule.value.end_date = d ? (d.toISOString().split('T')[0] ?? '') : ''
})

async function submit() {
  submitted.value = true
  if (!form.value.title.trim() || !form.value.date) return

  saving.value = true
  try {
    const payload: TrainingSessionCreate = {
      ...form.value,
      recurrence_rule: hasRecurrence.value ? recurrenceRule.value : null,
    }

    if (props.initialData?.id) {
      await trainingStore.updateSession(props.initialData.id, payload)
      emit('success', props.initialData.id)
    } else {
      const session = await trainingStore.createSession(payload)
      if (session) emit('success', session.id)
    }
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
</style>
