<template>
  <Dialog
    v-model:visible="visible"
    header="Excel-Export – Spalten auswählen"
    :style="{ width: '640px' }"
    :modal="true"
    :draggable="false"
  >
    <div class="export-dialog-content">
      <p class="hint">Wählen Sie die Spalten, die in der Excel-Datei enthalten sein sollen.</p>

      <div class="column-groups">
        <div
          v-for="group in columnGroups"
          :key="group.label"
          class="column-group"
        >
          <div class="group-header">
            <span class="group-label">{{ group.label }}</span>
            <div class="group-actions">
              <Button
                label="Alle"
                size="small"
                text
                @click="selectGroup(group)"
              />
              <Button
                label="Keine"
                size="small"
                text
                severity="secondary"
                @click="deselectGroup(group)"
              />
            </div>
          </div>
          <div class="column-checkboxes">
            <div
              v-for="col in group.columns"
              :key="col.key"
              class="column-checkbox-item"
            >
              <Checkbox
                v-model="selectedColumns"
                :inputId="col.key"
                :value="col.key"

              />
              <label :for="col.key" class="column-label">{{ col.label }}</label>
            </div>
          </div>
        </div>
      </div>

      <div class="selection-summary">
        <span>{{ selectedColumns.length }} Spalte(n) ausgewählt</span>
        <div>
          <Button label="Alle auswählen" size="small" text @click="selectAll" />
          <Button label="Alle abwählen" size="small" text severity="secondary" @click="deselectAll" />
        </div>
      </div>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" outlined @click="visible = false" />
      <Button
        label="Exportieren"
        icon="pi pi-file-excel"
        severity="success"
        :disabled="selectedColumns.length === 0"
        :loading="exporting"
        @click="handleExport"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'

interface ColumnDef {
  key: string
  label: string
}

interface ColumnGroup {
  label: string
  columns: ColumnDef[]
}

const props = defineProps<{
  modelValue: boolean
  exporting: boolean
  extraColumnGroups?: ColumnGroup[]
  extraDefaultColumns?: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  export: [columns: string[]]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const baseColumnGroups: ColumnGroup[] = [
  {
    label: 'Mitgliedsdaten',
    columns: [
      { key: 'name', label: 'Vorname' },
      { key: 'lastname', label: 'Nachname' },
      { key: 'gender', label: 'Geschlecht' },
      { key: 'birthday', label: 'Geburtsdatum' },
      { key: 'age', label: 'Alter' },
      { key: 'email', label: 'E-Mail' },
      { key: 'phone', label: 'Telefon' },
      { key: 'mobile', label: 'Mobil' },
      { key: 'street', label: 'Straße' },
      { key: 'zip_code', label: 'PLZ' },
      { key: 'city', label: 'Stadt' },
      { key: 'joined', label: 'Eingetreten am' },
      { key: 'status', label: 'Status' },
      { key: 'group', label: 'Gruppe' },
      { key: 'departments', label: 'Abteilungen' },
      { key: 'identityCardNumber', label: 'Ausweisnummer' },
      { key: 'canSwimm', label: 'Schwimmer' },
      { key: 'notes', label: 'Notizen' },
    ],
  },
  {
    label: 'Elternteil 1',
    columns: [
      { key: 'parent1_name', label: 'Vorname' },
      { key: 'parent1_lastname', label: 'Nachname' },
      { key: 'parent1_email', label: 'E-Mail' },
      { key: 'parent1_email2', label: 'E-Mail 2' },
      { key: 'parent1_phone', label: 'Telefon' },
      { key: 'parent1_mobile', label: 'Mobil' },
      { key: 'parent1_street', label: 'Straße' },
      { key: 'parent1_zip_code', label: 'PLZ' },
      { key: 'parent1_city', label: 'Stadt' },
    ],
  },
  {
    label: 'Elternteil 2',
    columns: [
      { key: 'parent2_name', label: 'Vorname' },
      { key: 'parent2_lastname', label: 'Nachname' },
      { key: 'parent2_email', label: 'E-Mail' },
      { key: 'parent2_email2', label: 'E-Mail 2' },
      { key: 'parent2_phone', label: 'Telefon' },
      { key: 'parent2_mobile', label: 'Mobil' },
      { key: 'parent2_street', label: 'Straße' },
      { key: 'parent2_zip_code', label: 'PLZ' },
      { key: 'parent2_city', label: 'Stadt' },
    ],
  },
]

const columnGroups = computed<ColumnGroup[]>(() => [
  ...baseColumnGroups,
  ...(props.extraColumnGroups ?? []),
])

const allColumns = computed(() => columnGroups.value.flatMap((g) => g.columns.map((c) => c.key)))

const defaultColumns = [
  'name', 'lastname', 'gender', 'birthday', 'email', 'phone', 'mobile',
  'street', 'zip_code', 'city', 'joined', 'status', 'group',
]

const selectedColumns = ref<string[]>([...defaultColumns, ...(props.extraDefaultColumns ?? [])])

function selectGroup(group: ColumnGroup) {
  const keys = group.columns.map((c) => c.key)
  for (const key of keys) {
    if (!selectedColumns.value.includes(key)) {
      selectedColumns.value.push(key)
    }
  }
}

function deselectGroup(group: ColumnGroup) {
  const keys = new Set(group.columns.map((c) => c.key))
  selectedColumns.value = selectedColumns.value.filter((k) => !keys.has(k))
}

function selectAll() {
  selectedColumns.value = [...allColumns.value]
}

function deselectAll() {
  selectedColumns.value = []
}

function handleExport() {
  emit('export', [...selectedColumns.value])
}
</script>

<style scoped>
.export-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.hint {
  color: var(--text-color-secondary);
  margin: 0;
  font-size: 0.9rem;
}

.column-groups {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.column-group {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 0.75rem;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.group-label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-color);
}

.group-actions {
  display: flex;
  gap: 0.25rem;
}

.column-checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.4rem 0.75rem;
}

.column-checkbox-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.column-label {
  font-size: 0.875rem;
  cursor: pointer;
  user-select: none;
}

.selection-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}
</style>
