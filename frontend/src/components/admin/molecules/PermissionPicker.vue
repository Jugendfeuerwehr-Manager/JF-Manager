<template>
  <div class="permission-picker">
    <div class="picker-header flex align-items-center gap-2 mb-2">
      <InputText
        v-model="search"
        placeholder="Berechtigungen suchen..."
        size="small"
        class="flex-1"
      />
      <Button
        :label="allSelected ? 'Alle abwählen' : 'Alle wählen'"
        size="small"
        severity="secondary"
        text
        @click="toggleAll"
      />
    </div>

    <small class="picker-hint mb-2">
      Tipp: Berechtigungen sind nach Modul und Modell gruppiert. In der Matrix lassen sich Rechte schnell je Modell oder Aktion setzen.
    </small>

    <div class="permission-categories">
      <Accordion :multiple="true" :value="openPanels">
        <AccordionPanel v-for="cat in filteredCategories" :key="cat.label" :value="cat.label">
          <AccordionHeader>
            <div class="flex align-items-center gap-2 w-full">
              <i :class="cat.icon" />
              <span class="font-medium">{{ cat.label }}</span>
              <Badge
                :value="selectedCountFor(cat)"
                :severity="selectedCountFor(cat) > 0 ? 'success' : 'secondary'"
                class="ml-auto"
              />
            </div>
          </AccordionHeader>

          <AccordionContent>
            <div class="category-actions mb-2">
              <Button
                v-for="action in ACTIONS"
                :key="`${cat.label}-${action}`"
                :label="actionButtonLabel(cat, action)"
                size="small"
                text
                :severity="isActionSelected(cat, action) ? 'success' : 'secondary'"
                :disabled="actionPermissionIds(cat, action).length === 0"
                @click="toggleCategoryAction(cat, action)"
              />
            </div>

            <div class="matrix-wrapper">
              <table class="permission-matrix">
                <thead>
                  <tr>
                    <th>Modell</th>
                    <th v-for="action in ACTIONS" :key="`head-${cat.label}-${action}`">
                      {{ ACTION_LABEL[action] }}
                    </th>
                    <th>Alle</th>
                  </tr>
                </thead>

                <tbody>
                  <tr v-for="model in cat.models" :key="`${cat.label}-${model.modelKey}`">
                    <td class="model-cell">
                      <div class="model-title">{{ model.modelLabel }}</div>
                      <div class="model-subtitle">{{ model.modelKey }}</div>
                    </td>

                    <td
                      v-for="action in ACTIONS"
                      :key="`${cat.label}-${model.modelKey}-${action}`"
                      class="action-cell"
                    >
                      <template v-if="model.permissionsByAction[action]">
                        <div class="cell-content">
                          <Checkbox
                            :model-value="isPermissionSelected(model.permissionsByAction[action]!.id)"
                            :input-id="`perm-${model.permissionsByAction[action]!.id}`"
                            binary
                            @update:model-value="(val) => togglePermission(model.permissionsByAction[action]!.id, val)"
                          />
                          <PermissionInfoIcon
                            :description="displayPermissionDescription(model.permissionsByAction[action]!, cat.label)"
                          />
                        </div>
                      </template>
                      <span v-else class="no-permission">-</span>
                    </td>

                    <td class="action-cell">
                      <Checkbox
                        :model-value="isModelFullySelected(model)"
                        :input-id="`model-all-${cat.label}-${model.modelKey}`"
                        binary
                        @update:model-value="(val) => toggleModelAll(model, val)"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="cat.models.length === 0" class="text-center py-3 text-color-secondary">
              Keine Modelle für dieses Modul gefunden
            </div>
          </AccordionContent>
        </AccordionPanel>
      </Accordion>

      <div v-if="filteredCategories.length === 0" class="text-center py-4 text-color-secondary">
        <i class="pi pi-search mr-2" />
        Keine Berechtigungen gefunden
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Accordion from 'primevue/accordion'
import AccordionPanel from 'primevue/accordionpanel'
import AccordionHeader from 'primevue/accordionheader'
import AccordionContent from 'primevue/accordioncontent'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import PermissionInfoIcon from '@/components/admin/atoms/PermissionInfoIcon.vue'
import type { Permission, PermissionCategory } from '@/types/admin'

const props = defineProps<{
  modelValue: number[]
  categories: PermissionCategory[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: number[]]
}>()

const search = ref('')
const ACTIONS = ['view', 'add', 'change', 'delete'] as const

type PermissionAction = (typeof ACTIONS)[number]

const ACTION_LABEL: Record<PermissionAction, string> = {
  view: 'Ansehen',
  add: 'Erstellen',
  change: 'Bearbeiten',
  delete: 'Löschen',
}

interface ModelPermissionRow {
  modelKey: string
  modelLabel: string
  permissionsByAction: Partial<Record<PermissionAction, Permission>>
}

interface MatrixCategory {
  label: string
  icon: string
  permissions: Permission[]
  models: ModelPermissionRow[]
}

const openPanels = computed(() => props.categories.map((c) => c.label))

const filteredCategories = computed<MatrixCategory[]>(() => {
  const withModels = props.categories.map((cat) => ({
    ...cat,
    models: buildModelRows(cat.permissions),
  }))

  const q = search.value.toLowerCase().trim()
  if (!q) return withModels

  return withModels
    .map((cat) => {
      const filteredPermissions = cat.permissions.filter((p) => {
        const modelLabel = humanizeObjectName(p.model)
        return (
          p.name.toLowerCase().includes(q) ||
          p.codename.toLowerCase().includes(q) ||
          modelLabel.toLowerCase().includes(q) ||
          cat.label.toLowerCase().includes(q)
        )
      })

      return {
        ...cat,
        permissions: filteredPermissions,
        models: buildModelRows(filteredPermissions),
      }
    })
    .filter((cat) => cat.permissions.length > 0)
})

const allPermIds = computed(() => props.categories.flatMap((c) => c.permissions.map((p) => p.id)))

const allSelected = computed(
  () => allPermIds.value.length > 0 && allPermIds.value.every((id) => props.modelValue.includes(id)),
)

function actionFromCodename(codename: string): PermissionAction | null {
  for (const action of ACTIONS) {
    if (codename.startsWith(`${action}_`)) return action
  }
  return null
}

function humanizeObjectName(name: string): string {
  const map: Record<string, string> = {
    member: 'Mitglied',
    parent: 'Elternkontakt',
    order: 'Bestellung',
    orderitem: 'Bestellposition',
    orderableitem: 'Artikel',
    inventoryitem: 'Inventargegenstand',
    storagelocation: 'Lagerort',
    stocktransaction: 'Bestandsbuchung',
    service: 'Dienst',
    attendance: 'Anwesenheit',
    qualification: 'Qualifikation',
    qualificationtype: 'Qualifikationstyp',
    customuser: 'Benutzer',
    group: 'Gruppe',
  }

  const key = name.split(' ').join('').toLowerCase()
  return map[key] ?? name.charAt(0).toUpperCase() + name.slice(1)
}

function buildModelRows(perms: Permission[]): ModelPermissionRow[] {
  const byModel = new Map<string, ModelPermissionRow>()

  for (const perm of perms) {
    const modelKey = perm.model
    if (!byModel.has(modelKey)) {
      byModel.set(modelKey, {
        modelKey,
        modelLabel: humanizeObjectName(modelKey),
        permissionsByAction: {},
      })
    }

    const action = actionFromCodename(perm.codename)
    if (action) {
      byModel.get(modelKey)!.permissionsByAction[action] = perm
    }
  }

  return Array.from(byModel.values()).sort((a, b) => a.modelLabel.localeCompare(b.modelLabel, 'de'))
}

function selectedCountFor(cat: MatrixCategory): number {
  return cat.permissions.filter((p) => props.modelValue.includes(p.id)).length
}

function isPermissionSelected(id: number): boolean {
  return props.modelValue.includes(id)
}

function togglePermission(id: number, checked: boolean): void {
  const current = new Set(props.modelValue)
  if (checked) {
    current.add(id)
  } else {
    current.delete(id)
  }
  emit('update:modelValue', Array.from(current))
}

function toggleAll(): void {
  if (allSelected.value) {
    emit('update:modelValue', [])
  } else {
    emit('update:modelValue', [...allPermIds.value])
  }
}

function actionPermissionIds(cat: MatrixCategory, action: PermissionAction): number[] {
  return cat.permissions.filter((p) => p.codename.startsWith(`${action}_`)).map((p) => p.id)
}

function isActionSelected(cat: MatrixCategory, action: PermissionAction): boolean {
  const ids = actionPermissionIds(cat, action)
  return ids.length > 0 && ids.every((id) => props.modelValue.includes(id))
}

function toggleCategoryAction(cat: MatrixCategory, action: PermissionAction): void {
  const ids = actionPermissionIds(cat, action)
  const current = new Set(props.modelValue)
  const currentlySelected = ids.length > 0 && ids.every((id) => current.has(id))

  if (currentlySelected) {
    ids.forEach((id) => current.delete(id))
  } else {
    ids.forEach((id) => current.add(id))
  }

  emit('update:modelValue', Array.from(current))
}

function actionButtonLabel(cat: MatrixCategory, action: PermissionAction): string {
  const count = actionPermissionIds(cat, action).length
  return `${ACTION_LABEL[action]} (${count})`
}

function modelPermissionIds(model: ModelPermissionRow): number[] {
  return ACTIONS.map((action) => model.permissionsByAction[action]?.id).filter(
    (id): id is number => id !== undefined,
  )
}

function isModelFullySelected(model: ModelPermissionRow): boolean {
  const ids = modelPermissionIds(model)
  return ids.length > 0 && ids.every((id) => props.modelValue.includes(id))
}

function toggleModelAll(model: ModelPermissionRow, checked: boolean): void {
  const ids = modelPermissionIds(model)
  const current = new Set(props.modelValue)

  if (checked) {
    ids.forEach((id) => current.add(id))
  } else {
    ids.forEach((id) => current.delete(id))
  }

  emit('update:modelValue', Array.from(current))
}

function displayPermissionDescription(perm: Permission, categoryLabel: string): string {
  const action = actionFromCodename(perm.codename)
  const actionLabel = action ? ACTION_LABEL[action].toLowerCase() : 'nutzen'
  return `Modul ${categoryLabel}: Erlaubt ${actionLabel} von ${humanizeObjectName(perm.model)}.`
}
</script>

<style scoped>
.permission-picker {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.permission-categories {
  overflow-y: auto;
  flex: 1;
}

.picker-hint {
  color: var(--p-text-muted-color);
  display: block;
}

.category-actions {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.matrix-wrapper {
  overflow-x: auto;
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
}

.permission-matrix {
  width: 100%;
  border-collapse: collapse;
  min-width: 680px;
}

.permission-matrix th,
.permission-matrix td {
  border-bottom: 1px solid var(--p-content-border-color);
  padding: 0.5rem;
  text-align: center;
  vertical-align: middle;
}

.permission-matrix th:first-child,
.permission-matrix td:first-child {
  text-align: left;
}

.permission-matrix tbody tr:hover {
  background: var(--p-content-hover-background);
}

.model-cell {
  min-width: 220px;
}

.model-title {
  font-weight: 600;
}

.model-subtitle {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.action-cell {
  min-width: 84px;
}

.cell-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
}

.no-permission {
  color: var(--p-text-muted-color);
}

@media (max-width: 768px) {
  .picker-header {
    flex-wrap: wrap;
  }

  .picker-header :deep(.p-inputtext) {
    width: 100%;
  }

  .category-actions :deep(.p-button) {
    font-size: 0.75rem;
    padding-inline: 0.5rem;
  }

  .permission-matrix {
    min-width: 560px;
  }

  .model-cell {
    min-width: 180px;
  }
}
</style>
