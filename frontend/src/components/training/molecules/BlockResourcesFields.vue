<template>
  <fieldset class="resources">
    <legend>Ausbilder und Material</legend>
    <div class="field">
      <label for="block-instructors">Ausbilder</label>
      <MultiSelect
        input-id="block-instructors"
        :model-value="instructors.map((i) => i.id)"
        :options="instructorChoices"
        option-label="name"
        option-value="id"
        filter
        display="chip"
        :loading="loadingInstructors"
        placeholder="Ausbilder wählen"
        @update:model-value="setInstructors"
      />
      <Message v-if="instructorError" severity="error" size="small" :closable="false">{{ instructorError }}</Message>
    </div>

    <div class="field">
      <span class="resources__label" id="block-materials-label">Materialbedarf</span>
      <p class="resources__hint">Nur Planung: Bestand und Verfügbarkeit im Inventar ändern sich nicht.</p>
      <ul v-if="materials.length" class="resources__materials" aria-labelledby="block-materials-label">
        <li v-for="(row, index) in materials" :key="index" class="resources__material">
          <AutoComplete
            :model-value="row.item ? { id: row.item, name: itemName(row) } : row.label"
            :suggestions="suggestions"
            option-label="name"
            :input-id="`material-item-${index}`"
            :aria-label="`Material ${index + 1}: Artikel oder Bezeichnung`"
            placeholder="Artikel suchen oder Bezeichnung"
            dropdown
            @complete="search($event.query)"
            @update:model-value="setItem(index, $event)"
          />
          <Select
            v-if="variantsOf(row).length"
            :model-value="row.variant"
            :options="variantsOf(row)"
            option-label="label"
            option-value="id"
            show-clear
            placeholder="Variante"
            :aria-label="`Material ${index + 1}: Variante`"
            @update:model-value="update(index, { variant: $event ?? null })"
          />
          <span v-else aria-hidden="true"></span>
          <InputNumber
            :model-value="row.quantity"
            :min="1"
            :max="100000"
            :input-id="`material-qty-${index}`"
            :aria-label="`Material ${index + 1}: Menge`"
            class="resources__qty"
            @update:model-value="update(index, { quantity: Math.max(1, $event ?? 1) })"
          />
          <Button icon="pi pi-trash" text severity="danger" :aria-label="`Material ${index + 1} entfernen`" @click="remove(index)" />
        </li>
      </ul>
      <Button label="Material hinzufügen" icon="pi pi-plus" text size="small" class="resources__add" @click="add" />
    </div>
  </fieldset>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import AutoComplete from 'primevue/autocomplete'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Select from 'primevue/select'
import { trainingSessionsApi } from '@/api/training'
import type { BlockMaterial, InstructorMini, MaterialOption } from '@/types/training'

const props = defineProps<{ sessionId: number | null; instructors: InstructorMini[]; materials: BlockMaterial[] }>()
const emit = defineEmits<{ 'update:instructors': [value: InstructorMini[]]; 'update:materials': [value: BlockMaterial[]] }>()

const options = ref<InstructorMini[]>([])
const loadingInstructors = ref(false)
const instructorError = ref('')
const suggestions = ref<MaterialOption[]>([])
// Known items (search results and saved rows) for names and variants.
const known = ref(new Map<number, MaterialOption>())

// Saved instructors stay visible even if they are no longer eligible; saving then reports it.
const instructorChoices = computed(() => {
  const byId = new Map(options.value.map((o) => [o.id, o]))
  for (const instructor of props.instructors) if (!byId.has(instructor.id)) byId.set(instructor.id, instructor)
  return [...byId.values()]
})

async function loadInstructors() {
  if (!props.sessionId || props.sessionId < 0) return
  loadingInstructors.value = true
  instructorError.value = ''
  try {
    options.value = (await trainingSessionsApi.instructorOptions(props.sessionId)).data
  } catch {
    instructorError.value = 'Ausbilderliste konnte nicht geladen werden.'
  } finally {
    loadingInstructors.value = false
  }
}

function setInstructors(ids: number[]) {
  emit('update:instructors', instructorChoices.value.filter((o) => ids.includes(o.id)))
}

async function search(query: string) {
  if (!props.sessionId) return
  try {
    suggestions.value = (await trainingSessionsApi.materialOptions(props.sessionId, query)).data
    for (const option of suggestions.value) known.value.set(option.id, option)
  } catch {
    suggestions.value = []
  }
}

function itemName(row: BlockMaterial) {
  return known.value.get(row.item ?? -1)?.name ?? row.label
}

function variantsOf(row: BlockMaterial) {
  return row.item ? known.value.get(row.item)?.variants ?? [] : []
}

function update(index: number, patch: Partial<BlockMaterial>) {
  const next = props.materials.map((row, i) => (i === index ? { ...row, ...patch } : row))
  const row = next[index]!
  // Keep the display name in sync with the chosen item/variant; free text stays as typed.
  if (row.item) {
    const option = known.value.get(row.item)
    const variant = option?.variants.find((v) => v.id === row.variant)
    row.label = variant?.label ?? option?.name ?? row.label
  }
  emit('update:materials', next)
}

function setItem(index: number, value: MaterialOption | string | null) {
  if (value && typeof value === 'object') {
    known.value.set(value.id, value)
    update(index, { item: value.id, variant: null, label: value.name })
  } else {
    update(index, { item: null, variant: null, label: value ?? '' })
  }
}

function add() {
  emit('update:materials', [...props.materials, { item: null, variant: null, quantity: 1, label: '' }])
}

function remove(index: number) {
  emit('update:materials', props.materials.filter((_, i) => i !== index))
}

watch(() => props.sessionId, () => { void loadInstructors() }, { immediate: true })
</script>

<style scoped>
.resources { display: grid; gap: var(--jf-space-2); margin: 0; padding: var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); min-width: 0; }
.resources legend { padding: 0 var(--jf-space-1); font-weight: var(--jf-weight-semibold); }
.field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.field label, .resources__label { font-size: 0.875rem; font-weight: 500; color: var(--text-color-secondary); }
.resources__hint { margin: 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.resources__materials { display: grid; gap: var(--jf-space-1); margin: 0; padding: 0; list-style: none; }
.resources__material { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) 6rem auto; gap: var(--jf-space-1); align-items: center; }
.resources__material :deep(.p-autocomplete) { min-width: 0; }
.resources__qty :deep(input) { width: 100%; }
.resources__add { justify-self: start; }
@media (max-width: 640px) { .resources__material { grid-template-columns: minmax(0, 1fr) 5rem auto; } .resources__material > :nth-child(2) { grid-column: 1 / -1; grid-row: 2; } .resources__material > span:nth-child(2) { display: none; } }
</style>
