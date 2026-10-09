<template>
  <div class="picker">
    <p v-if="loading" class="picker__hint" role="status">Wird geladen …</p>
    <template v-else>
      <p class="picker__hint">
        <template v-if="current?.staffing_template || current?.slots.length">
          Aktuell: {{ current?.name ?? 'Besetzung aus der gespeicherten Übung' }}<template v-if="current?.slots.length"> · {{ current.slots.map(s => `${s.label} (${s.min}/${s.max})`).join(', ') }}</template>
        </template>
        <template v-else>Keine Besetzung hinterlegt. Neue Übungen nutzen die Standards der Abteilung.</template>
      </p>
      <div class="picker__row">
        <label :for="`picker-${templateId}`" class="sr-only">Besetzungsvorlage für {{ title }}</label>
        <select :id="`picker-${templateId}`" v-model="selected" class="picker__input">
          <option :value="null">Keine Besetzungsvorlage</option>
          <option v-for="t in options" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
        <Button label="Übernehmen" size="small" severity="secondary" :loading="saving" @click="save" />
      </div>
      <p v-if="error" class="picker__error" role="alert">{{ error }}</p>
      <p v-if="saved" class="picker__hint" role="status"><i class="pi pi-check" aria-hidden="true"></i> Gespeichert. Neue Übungen aus dieser Vorlage erhalten eine eigene Kopie.</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import { staffingTemplatesApi, type StaffingTemplate, type TrainingTemplateStaffing } from '@/api/participation'
import { getApiErrorMessage } from '@/utils/apiError'

/** PART-04.5: carry a staffing template into an exercise template (copied, independent). */
const props = defineProps<{ templateId: number, department: number | null, title: string }>()

const current = ref<TrainingTemplateStaffing | null>(null)
const options = ref<StaffingTemplate[]>([])
const selected = ref<number | null>(null)
const loading = ref(true)
const saving = ref(false)
const saved = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  try {
    const [staffing, list] = await Promise.all([
      staffingTemplatesApi.trainingTemplate(props.templateId),
      staffingTemplatesApi.list({ department: props.department }),
    ])
    current.value = staffing.data
    options.value = list.data.results
    selected.value = staffing.data.staffing_template
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Die Besetzung konnte nicht geladen werden.')
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  saved.value = false
  error.value = null
  try {
    current.value = (await staffingTemplatesApi.setTrainingTemplate(props.templateId, selected.value)).data
    saved.value = true
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Die Besetzung konnte nicht gespeichert werden.')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.picker { display: grid; gap: var(--jf-space-1); }
.picker p { margin: 0; }
.picker__row { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); align-items: center; }
.picker__row :deep(.p-button) { min-height: var(--jf-touch-target); }
.picker__input { min-height: var(--jf-touch-target); flex: 1 1 12rem; padding: 0 var(--jf-space-1); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-sm); background: var(--jf-color-card); color: var(--jf-color-text); font: inherit; }
.picker__hint { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.picker__error { color: var(--p-red-600); font-size: var(--jf-text-sm); }
.app-dark .picker__error { color: var(--p-red-300); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
</style>
