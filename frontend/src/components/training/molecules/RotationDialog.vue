<template>
  <Dialog :visible="visible" header="Rotation planen" modal :style="{ width: '980px', maxWidth: 'calc(100vw - 24px)' }" @update:visible="emit('update:visible', $event)">
    <div class="rotation">
      <p v-if="!groupChoices.length" role="alert">Die Übung hat noch keine Gruppen. Gruppen in den Einstellungen der Übung festlegen.</p>
      <template v-else>
        <section class="rotation__setup" aria-label="Rahmen">
          <div class="field">
            <label for="rotation-groups">Gruppen</label>
            <MultiSelect input-id="rotation-groups" v-model="groupIds" :options="groupChoices" option-label="name" option-value="id" />
          </div>
          <div class="field">
            <label for="rotation-start">Beginn (Minute ab Übungsbeginn)</label>
            <InputNumber input-id="rotation-start" v-model="startOffset" :min="0" :max="duration" />
          </div>
          <div class="field">
            <label for="rotation-duration">Stationsdauer (Min.)</label>
            <InputNumber input-id="rotation-duration" v-model="stationDuration" :min="1" :max="480" />
          </div>
          <div class="field">
            <label for="rotation-transition">Wechselzeit (Min.)</label>
            <InputNumber input-id="rotation-transition" v-model="transition" :min="0" :max="120" />
          </div>
          <div class="field">
            <label for="rotation-break">Pause</label>
            <Select input-id="rotation-break" v-model="breakChoice" :options="breakOptions" option-label="label" option-value="value" />
          </div>
          <div v-if="breakAfterRound !== null" class="field">
            <label for="rotation-break-duration">Pausendauer (Min.)</label>
            <InputNumber input-id="rotation-break-duration" v-model="breakDuration" :min="1" :max="240" />
          </div>
        </section>

        <section aria-labelledby="rotation-stations-heading" class="rotation__stations">
          <h3 id="rotation-stations-heading">Stationen in Reihenfolge</h3>
          <p class="rotation__muted rotation__hint">
            Jede Station wird für alle gewählten Gruppen verknüpft angelegt: Eine Änderung an Station 1 gilt für jede Gruppe.
            Für eine Altersgruppe lässt sich die Verknüpfung im Baustein lösen.
          </p>
          <ol>
            <li v-for="(station, index) in stations" :key="station.key" class="rotation__station">
              <span class="rotation__index" aria-hidden="true">{{ index + 1 }}.</span>
              <div class="rotation__fields">
                <AutoComplete
                  :model-value="station.libraryBlock ? { id: station.libraryBlock, title: station.title } : null"
                  :suggestions="librarySuggestions"
                  option-label="title"
                  dropdown
                  force-selection
                  :input-id="`rotation-library-${index}`"
                  :aria-label="`Station ${index + 1}: Baustein aus der Bibliothek`"
                  placeholder="Aus Bibliothek wählen (optional)"
                  @complete="searchLibrary($event.query)"
                  @update:model-value="(value: LibraryBlockList | null) => chooseLibrary(station, value)"
                />
                <InputText v-model="station.title" :aria-label="`Station ${index + 1}: Titel`" placeholder="Titel" />
                <InputText v-model="station.location" :aria-label="`Station ${index + 1}: Ort`" placeholder="Ort" />
                <MultiSelect
                  :model-value="station.instructors.map((i) => i.id)"
                  :options="instructorOptions"
                  option-label="name"
                  option-value="id"
                  filter
                  placeholder="Ausbilder"
                  :aria-label="`Station ${index + 1}: Ausbilder`"
                  @update:model-value="(ids: number[]) => (station.instructors = instructorOptions.filter((o) => ids.includes(o.id)))"
                />
                <p v-if="station.libraryBlock" class="rotation__muted rotation__source">
                  <i class="pi pi-book" aria-hidden="true"></i> Inhalt aus der Bibliothek wird übernommen
                </p>
              </div>
              <span class="rotation__order">
                <Button icon="pi pi-arrow-up" text size="small" :disabled="index === 0" :aria-label="`Station ${index + 1} nach oben`" @click="move(index, -1)" />
                <Button icon="pi pi-arrow-down" text size="small" :disabled="index === stations.length - 1" :aria-label="`Station ${index + 1} nach unten`" @click="move(index, 1)" />
                <Button icon="pi pi-trash" text size="small" severity="danger" :aria-label="`Station ${index + 1} entfernen`" @click="stations.splice(index, 1)" />
              </span>
            </li>
          </ol>
          <Button label="Station hinzufügen" icon="pi pi-plus" text size="small" @click="addStation" />
        </section>

        <section aria-labelledby="rotation-preview-heading" class="rotation__preview">
          <h3 id="rotation-preview-heading">Vorschau</h3>
          <Message v-if="preview.error" severity="warn" :closable="false">{{ preview.error }}</Message>
          <template v-else-if="preview.plan">
            <p class="rotation__summary" role="status">
              {{ preview.plan.rounds.length }} Runden · {{ clock(preview.plan.rounds[0]!.start) }}–{{ clock(preview.plan.end) }} ·
              {{ preview.plan.blocks.length }} Bausteine werden als ein rückgängig machbarer Schritt angelegt
            </p>
            <div class="rotation__table">
              <table>
                <thead>
                  <tr><th scope="col">Runde</th><th v-for="group in selectedGroups" :key="group.id" scope="col">{{ group.name }}</th><th scope="col">Unbesetzt</th></tr>
                </thead>
                <tbody>
                  <template v-for="(round, index) in preview.plan.rounds" :key="round.number">
                    <tr>
                      <th scope="row">{{ round.number }} · {{ clock(round.start) }}–{{ clock(round.end) }}</th>
                      <td v-for="cell in round.cells" :key="cell.group.id">
                        <template v-if="cell.station">{{ cell.station.title }}</template>
                        <StatusBadge v-else label="Freie Runde" severity="info" />
                      </td>
                      <td class="rotation__muted">{{ round.idleStations.map((s) => s.title).join(', ') || '–' }}</td>
                    </tr>
                    <tr v-if="betweenRounds[index]" class="rotation__between">
                      <td :colspan="selectedGroups.length + 2">{{ betweenRounds[index] }}</td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </template>
        </section>
      </template>
    </div>
    <template #footer>
      <Button label="Abbrechen" severity="secondary" @click="emit('update:visible', false)" />
      <Button label="In den Entwurf übernehmen" icon="pi pi-check" :disabled="!preview.plan || applying" :loading="applying" @click="apply" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { libraryApi, trainingSessionsApi } from '@/api/training'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'
import type { InstructorMini, LibraryBlockList } from '@/types/training'
import { buildRotation, newStationKey, type RotationStation } from '../utils/rotation'

const props = defineProps<{ visible: boolean; duration: number }>()
const emit = defineEmits<{ 'update:visible': [visible: boolean] }>()
const planner = useTrainingPlannerStore()

const groupChoices = computed(() => planner.session?.groups ?? [])
const groupIds = ref<number[]>([])
const stations = ref<RotationStation[]>([])
const startOffset = ref(0)
const stationDuration = ref(20)
const transition = ref(5)
const breakAfterRound = ref<number | null>(null)
const breakDuration = ref(10)
const breakChoice = computed({
  get: () => breakAfterRound.value ?? 0,
  set: (value: number) => { breakAfterRound.value = value || null },
})
const instructorOptions = ref<InstructorMini[]>([])
const librarySuggestions = ref<LibraryBlockList[]>([])
const applying = ref(false)

const selectedGroups = computed(() => groupChoices.value.filter((g) => groupIds.value.includes(g.id)))
const roundCount = computed(() => Math.max(selectedGroups.value.length, stations.value.length))
const breakOptions = computed(() => [
  { value: 0, label: 'Keine Pause' },
  ...Array.from({ length: Math.max(0, roundCount.value - 1) }, (_, i) => ({ value: i + 1, label: `Nach Runde ${i + 1}` })),
])

const preview = computed(() => {
  try {
    const plan = buildRotation({
      groups: selectedGroups.value,
      stations: stations.value,
      startOffset: startOffset.value ?? 0,
      stationDuration: stationDuration.value ?? 0,
      transition: transition.value ?? 0,
      breakAfterRound: breakAfterRound.value,
      breakDuration: breakDuration.value ?? 0,
      sessionDuration: props.duration,
      allGroups: selectedGroups.value.length === groupChoices.value.length,
    }, planner.sessionId ?? 0)
    return { plan, error: '' }
  } catch (e) {
    return { plan: null, error: (e as Error).message }
  }
})

// Change-over or pause between round i and i+1, shown as its own preview row.
const betweenRounds = computed(() => {
  const plan = preview.value.plan
  if (!plan) return []
  return plan.rounds.map((round, index) => {
    if (index === plan.rounds.length - 1) return ''
    const block = plan.blocks.find((b) => (b.kind === 'transition' || b.kind === 'break') && b.start_offset_minutes === round.end)
    if (!block) return ''
    return `${block.kind === 'break' ? 'Pause' : 'Wechsel'} ${clock(block.start_offset_minutes!)}–${clock(block.start_offset_minutes! + block.duration_minutes!)}`
  })
})

function clock(offset: number) {
  const [h, m] = (planner.session?.start_time ?? '00:00').split(':').map(Number)
  const total = (h ?? 0) * 60 + (m ?? 0) + offset
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

function freeStation(title = ''): RotationStation {
  return { key: newStationKey(), title, location: '', instructors: [], libraryBlock: null }
}

function addStation() {
  stations.value.push(freeStation())
}

async function searchLibrary(query: string) {
  try {
    librarySuggestions.value = (await libraryApi.list({ search: query || undefined, page_size: 30 })).data.results
  } catch {
    librarySuggestions.value = []
  }
}

// A library block fills title, duration hint and content; the planned blocks own copies.
async function chooseLibrary(station: RotationStation, value: LibraryBlockList | string | null) {
  if (!value || typeof value !== 'object') {
    if (value === null && station.libraryBlock) {
      Object.assign(station, { libraryBlock: null, content: undefined, color: undefined, learningObjective: undefined })
    }
    return
  }
  Object.assign(station, { libraryBlock: value.id, title: value.title, color: value.color || undefined })
  try {
    const detail = (await libraryApi.get(value.id)).data
    if (station.libraryBlock !== value.id) return
    Object.assign(station, {
      content: detail.content || undefined,
      color: detail.color || undefined,
      learningObjective: detail.description || undefined,
    })
  } catch {
    // Without details the server still copies the library content when the plan is saved.
  }
}

function move(index: number, delta: number) {
  const list = stations.value
  const [item] = list.splice(index, 1)
  list.splice(index + delta, 0, item!)
}

async function apply() {
  if (!preview.value.plan || applying.value) return
  applying.value = true
  try {
    await planner.addBlocks(preview.value.plan.blocks)
    emit('update:visible', false)
  } finally {
    applying.value = false
  }
}

watch(roundCount, () => {
  if (breakAfterRound.value !== null && breakAfterRound.value >= roundCount.value) breakAfterRound.value = null
})

watch(
  () => props.visible,
  async (visible) => {
    if (!visible) return
    groupIds.value = groupChoices.value.map((g) => g.id)
    stations.value = [1, 2, 3].slice(0, Math.max(1, groupIds.value.length)).map((n) => freeStation(`Station ${n}`))
    // Start after the existing plan so nothing overlaps by default.
    startOffset.value = Math.min(props.duration, Math.max(0, ...planner.blocks.map((b) => b.start_offset_minutes + b.duration_minutes)))
    if (planner.sessionId) {
      try { instructorOptions.value = (await trainingSessionsApi.instructorOptions(planner.sessionId)).data }
      catch { instructorOptions.value = [] }
    }
  },
  { immediate: true },
)
</script>

<style scoped>
.rotation { display: grid; gap: var(--jf-space-3); }
.rotation h3 { margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-md); }
.rotation p { margin: 0; }
.rotation__setup { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: var(--jf-space-2); }
.field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.field label { font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); color: var(--jf-color-text-muted); }
.field :deep(.p-inputnumber), .field :deep(.p-inputnumber-input) { width: 100%; min-width: 0; }
.rotation__stations ol { display: grid; gap: var(--jf-space-1); margin: 0 0 var(--jf-space-1); padding: 0; list-style: none; }
.rotation__hint { margin-bottom: var(--jf-space-1) !important; font-size: var(--jf-text-sm); }
.rotation__station { display: grid; grid-template-columns: 1.5rem minmax(0, 1fr) auto; gap: var(--jf-space-1); align-items: start; padding: var(--jf-space-1) 0; border-bottom: 1px solid var(--jf-color-border); }
.rotation__index { padding-top: 0.6rem; }
.rotation__fields { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: var(--jf-space-1); min-width: 0; }
.rotation__fields :deep(.p-autocomplete), .rotation__fields :deep(.p-multiselect) { min-width: 0; width: 100%; }
.rotation__source { grid-column: 1 / -1; margin: 0; font-size: var(--jf-text-sm); }
.rotation__index { color: var(--jf-color-text-muted); }
.rotation__order { display: flex; }
.rotation__summary { font-weight: var(--jf-weight-semibold); margin-bottom: var(--jf-space-1) !important; }
.rotation__table { overflow: auto; max-height: 40vh; }
.rotation table { width: 100%; border-collapse: collapse; }
.rotation th, .rotation td { text-align: left; border-bottom: 1px solid var(--jf-color-border); padding: var(--jf-space-1); white-space: nowrap; }
.rotation__between td { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.rotation__muted { color: var(--jf-color-text-muted); }
@media (max-width: 720px) {
  .rotation__fields { grid-template-columns: minmax(0, 1fr); }
}
</style>
