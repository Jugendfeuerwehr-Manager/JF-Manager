<template>
  <Dialog
    v-model:visible="visible"
    :header="`Austritt erfassen: ${memberName}`"
    :modal="true"
    :closable="!loading"
    :close-on-escape="!loading"
    style="max-width: 560px; width: 95vw"
  >
    <form class="leave-form" novalidate @submit.prevent="submit">
      <div class="leave-form__field">
        <label for="leave-date">Austrittsdatum</label>
        <DatePicker
          v-model="leftAt"
          input-id="leave-date"
          update-model-type="date"
          date-format="dd.mm.yy"
          show-icon
          :min-date="joinedDate ?? undefined"
          :invalid="!!error"
          aria-describedby="leave-date-hint"
        />
        <p id="leave-date-hint" class="leave-form__hint">
          Der Tag, an dem die Mitgliedschaft endet{{ joinedDate ? ` (frühestens am Eintrittstag, ${formatDate(joinedDate)})` : '' }}.
        </p>
        <p v-if="error" class="leave-form__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ error }}</p>
      </div>

      <fieldset class="leave-form__field leave-form__kinds">
        <legend>Art des Abgangs</legend>
        <label v-for="(label, value) in EXIT_KIND_LABELS" :key="value" class="leave-form__radio">
          <RadioButton v-model="kind" :input-id="`leave-kind-${value}`" :value="value" name="leave-kind" />
          <span>{{ label }}</span>
        </label>
      </fieldset>

      <div v-if="kind === 'exit_other'" class="leave-form__field">
        <label for="leave-reason">Grund <span class="leave-form__optional">(für die Jahresmeldung)</span></label>
        <Select
          v-model="exitReason"
          input-id="leave-reason"
          :options="reasonOptions"
          option-label="label"
          option-value="value"
          show-clear
          placeholder="Grund wählen"
        />
      </div>

      <div v-if="statuses.length" class="leave-form__field">
        <label for="leave-status">Neuer Status <span class="leave-form__optional">(optional)</span></label>
        <Select
          v-model="statusId"
          input-id="leave-status"
          :options="statuses"
          option-label="name"
          option-value="id"
          show-clear
          placeholder="Status beibehalten"
        />
      </div>

      <section class="leave-form__next" aria-labelledby="leave-next-title">
        <h3 id="leave-next-title">Was danach passiert</h3>
        <ul>
          <li>Das Mitglied bleibt sichtbar und ist als ausgetreten gekennzeichnet.</li>
          <li>
            Nach Ablauf der Aufbewahrungsfrist (Standard: 12 Monate, einstellbar unter Einstellungen › Datenschutz) wird es
            automatisch anonymisiert. 30 Tage vorher bekommt die Leitung eine Aufgabe im Eingang.
          </li>
          <li>Anwesenheiten und Qualifikationen bleiben für Dienstbuch und Statistik erhalten.</li>
          <li>Der Austritt lässt sich bis zur Anonymisierung zurücknehmen.</li>
        </ul>
      </section>

      <div class="leave-form__actions">
        <Button type="button" label="Abbrechen" severity="secondary" text :disabled="loading" @click="visible = false" />
        <Button type="submit" label="Austritt erfassen" icon="pi pi-sign-out" :loading="loading" />
      </div>
    </form>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import Button from 'primevue/button'
import RadioButton from 'primevue/radiobutton'
import type { Status } from '@/types/members'
import { EXIT_KIND_LABELS, EXIT_REASON_LABELS, type ExitKind, type ExitReason, type LeavePayload } from '@/types/membership'
import { toIsoDateLocal } from '@/utils/dateParsing'

interface Props {
  memberName: string
  joined?: string | null
  statuses: Status[]
  loading?: boolean
}

interface Emits {
  (e: 'confirm', payload: LeavePayload & { left_at: string }): void
}

const props = withDefaults(defineProps<Props>(), { joined: null, loading: false })
const emit = defineEmits<Emits>()
const visible = defineModel<boolean>({ required: true })

const leftAt = ref<Date | null>(new Date())
const statusId = ref<number | null>(null)
const kind = ref<ExitKind>('exit_other')
const exitReason = ref<ExitReason | null>(null)
const reasonOptions = Object.entries(EXIT_REASON_LABELS).map(([value, label]) => ({ value, label }))
const error = ref('')

const joinedDate = computed(() => (props.joined ? new Date(`${props.joined}T00:00:00`) : null))
const formatDate = (date: Date) => date.toLocaleDateString('de-DE')

// Suggest the stage that matches the kind of exit; stages without a category yet are matched by name.
const suggestedStatus = computed(() => {
  const category = kind.value === 'exit_ea' ? 'transferred' : 'left'
  const pattern = kind.value === 'exit_ea' ? /übertritt|einsatzabteilung/i : /austritt|ausgetreten|ehemalig/i
  const byCategory = props.statuses.find((status) => status.category === category)
  if (byCategory) return byCategory.id
  return props.statuses.find((status) => pattern.test(status.name))?.id ?? null
})

watch(kind, () => {
  statusId.value = suggestedStatus.value
  if (kind.value !== 'exit_other') exitReason.value = null
})

watch(visible, (open) => {
  if (!open) return
  leftAt.value = new Date()
  kind.value = 'exit_other'
  exitReason.value = null
  statusId.value = suggestedStatus.value
  error.value = ''
})

function submit() {
  error.value = ''
  if (!leftAt.value) {
    error.value = 'Bitte ein Austrittsdatum wählen.'
    return
  }
  if (joinedDate.value && leftAt.value < joinedDate.value) {
    error.value = 'Der Austritt kann nicht vor dem Eintritt liegen.'
    return
  }
  emit('confirm', {
    left_at: toIsoDateLocal(leftAt.value),
    kind: kind.value,
    exit_reason: exitReason.value ?? '',
    ...(statusId.value != null ? { status_id: statusId.value } : {})
  })
}
</script>

<style scoped>
.leave-form {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.leave-form__field {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
}

.leave-form__field label {
  font-weight: var(--jf-weight-semibold);
}

.leave-form__optional,
.leave-form__hint {
  font-weight: normal;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.leave-form__hint {
  margin: 0;
}

.leave-form__error {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin: 0;
  font-size: 0.8125rem;
  color: var(--p-red-700);
}

.leave-form__kinds {
  border: 0;
  margin: 0;
  padding: 0;
}

.leave-form__kinds legend {
  font-weight: var(--jf-weight-semibold);
  margin-bottom: var(--jf-space-0-5);
}

.leave-form__radio {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: 44px;
  font-weight: normal !important;
}

.leave-form__next {
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
}

.leave-form__next h3 {
  margin: 0 0 var(--jf-space-0-5);
  font-size: 0.875rem;
  font-weight: var(--jf-weight-semibold);
}

.leave-form__next ul {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.875rem;
  color: var(--jf-color-text-muted);
}

.leave-form__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}
</style>
