<template>
  <SettingsCategoryCard
    title="Zusatzfelder"
    description="Eigene Angaben am Mitglied, etwa Schule oder T-Shirt-Größe. Sie erscheinen in der Mitgliedsbearbeitung und lassen sich in Aufnahmeformularen abfragen."
    icon="pi pi-list-check"
  >
    <div class="fields-manager">
      <p v-if="store.error" class="fields-manager__error" role="alert">{{ store.error }}</p>
      <div v-if="store.loading" class="flex justify-content-center p-3">
        <ProgressSpinner style="width: 2rem; height: 2rem" />
      </div>
      <p v-else-if="!store.definitions.length" class="fields-manager__empty">
        <i class="pi pi-info-circle" aria-hidden="true"></i> Noch keine Zusatzfelder.
      </p>
      <ul v-else class="fields-manager__list">
        <li v-for="definition in store.definitions" :key="definition.id" class="fields-manager__row">
          <span class="fields-manager__label">{{ definition.label }}</span>
          <span class="fields-manager__meta">{{ TYPE_LABELS[definition.field_type] }}</span>
          <span class="fields-manager__meta">{{ scopeName(definition.department) }}</span>
          <label class="fields-manager__active">
            <Checkbox
              :model-value="definition.active"
              :binary="true"
              :disabled="!canEdit"
              @update:model-value="(active: boolean) => toggle(definition, active)"
            />
            Aktiv
          </label>
          <Button
            icon="pi pi-trash"
            text
            rounded
            size="small"
            severity="danger"
            :aria-label="`${definition.label} löschen`"
            :disabled="!canEdit || definition.in_use"
            :title="definition.in_use ? 'Mitglieder haben Angaben in diesem Feld; nur deaktivieren möglich.' : ''"
            @click="confirmDelete(definition)"
          />
        </li>
      </ul>
      <div>
        <Button label="Zusatzfeld anlegen" icon="pi pi-plus" size="small" :disabled="!canEdit" @click="dialogOpen = true" />
      </div>
    </div>
    <MemberFieldDialog :open="dialogOpen" :scopes="scopes" @close="dialogOpen = false" />
  </SettingsCategoryCard>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import ProgressSpinner from 'primevue/progressspinner'
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import MemberFieldDialog from '@/components/members/molecules/MemberFieldDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import { useMemberFieldsStore } from '@/stores/memberFields'
import type { MemberFieldDefinition, MemberFieldType } from '@/types/members'

const TYPE_LABELS: Record<MemberFieldType, string> = {
  text: 'Text',
  textarea: 'Mehrzeilig',
  number: 'Zahl',
  date: 'Datum',
  select: 'Auswahl',
  checkbox: 'Ja / Nein'
}

const store = useMemberFieldsStore()
const departmentsStore = useDepartmentsStore()
const auth = useAuthStore()
const confirm = useConfirm()
const dialogOpen = ref(false)

const canEdit = computed(() => auth.hasPerm('members.add_memberfielddefinition'))
// The server decides which of these the user may write to.
const scopes = computed(() => [
  { id: null, name: 'Ganze Organisation (alle Abteilungen)' },
  ...departmentsStore.departments.map((department) => ({ id: department.id, name: department.name }))
])

function scopeName(department: number | null) {
  if (department === null) return 'Organisation'
  return departmentsStore.departments.find((entry) => entry.id === department)?.name ?? 'Abteilung'
}

async function toggle(definition: MemberFieldDefinition, active: boolean) {
  try {
    await store.save({ active }, definition.id)
  } catch {
    // store.error is shown above the list
  }
}

function confirmDelete(definition: MemberFieldDefinition) {
  confirm.require({
    message: `Zusatzfeld „${definition.label}“ löschen?`,
    header: 'Löschen bestätigen',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: () => store.remove(definition.id).catch(() => undefined)
  })
}

onMounted(() => {
  store.fetchDefinitions()
  if (!departmentsStore.departments.length) departmentsStore.fetchDepartments()
})
</script>

<style scoped>
.fields-manager {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}

.fields-manager__list {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  margin: 0;
  padding: 0;
  list-style: none;
}

.fields-manager__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.fields-manager__label {
  flex: 1 1 10rem;
  font-weight: var(--jf-weight-medium);
}

.fields-manager__meta,
.fields-manager__empty {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.fields-manager__active {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  font-size: var(--jf-text-sm);
}

.fields-manager__error {
  margin: 0;
  color: var(--jf-color-danger);
}
</style>
