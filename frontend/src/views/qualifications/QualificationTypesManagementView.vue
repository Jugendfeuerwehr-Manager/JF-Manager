<template>
  <div class="type-management-view">
    <OverviewHeader
      title="Qualifikationstypen"
      subtitle="Verwalte Ablaufregeln und Beschreibungen deiner Qualifikationen"
      eyebrow="Verwaltung"
    >
      <template #actions>
        <Button
          label="Zurück"
          icon="pi pi-arrow-left"
          severity="secondary"
          outlined
          @click="router.push('/qualifications')"
        />
        <Button
          label="Neuer Typ"
          icon="pi pi-plus"
          @click="handleCreate"
        />
      </template>
    </OverviewHeader>

    <section class="type-management-toolbar">
      <div class="toolbar-card">
        <label for="type-search">Schnellsuche</label>
        <InputText
          id="type-search"
          v-model="typeSearch"
          placeholder="Name oder Beschreibung"
        />
      </div>
      <div class="toolbar-stats">
        <div class="stat-card">
          <span>Typen gesamt</span>
          <strong>{{ totalQualificationTypes }}</strong>
        </div>
        <div class="stat-card">
          <span>Mit Ablaufregel</span>
          <strong>{{ expiringTypesCount }}</strong>
        </div>
      </div>
    </section>

    <Card class="type-management-card">
      <template #title>Typenübersicht</template>
      <template #content>
        <div v-if="qualificationsStore.loadingTypes" class="loading-state">
          <ProgressSpinner />
        </div>
        <DataTable
          v-else
          :value="filteredQualificationTypes"
          :paginator="filteredQualificationTypes.length > 10"
          :rows="10"
          :rowsPerPageOptions="[10, 25, 50]"
          responsiveLayout="scroll"
          breakpoint="960px"
          stripedRows
        >
          <Column field="name" header="Name" sortable>
            <template #body="{ data }">
              <div class="name-with-tag">
                <span>{{ data.name }}</span>
                <Tag value="G" icon="pi pi-globe" severity="contrast" />
              </div>
            </template>
          </Column>
          <Column field="validity_period" header="Gültigkeit (Monate)" sortable>
            <template #body="{ data }">
              {{ data.validity_period || 'Unbegrenzt' }}
            </template>
          </Column>
          <Column field="description" header="Beschreibung">
            <template #body="{ data }">
              {{ data.description || '-' }}
            </template>
          </Column>
          <Column header="Aktionen" style="width: 140px">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-pencil"
                  text
                  rounded
                  size="small"
                  severity="info"
                  @click="handleEdit(data)"
                  v-tooltip.bottom="'Bearbeiten'"
                />
                <Button
                  icon="pi pi-trash"
                  text
                  rounded
                  size="small"
                  severity="danger"
                  @click="handleDelete(data)"
                  v-tooltip.bottom="'Löschen'"
                />
              </div>
            </template>
          </Column>
          <template #empty>
            <div class="empty-state">
              <i class="pi pi-book"></i>
              <p>
                {{ typeSearch ? 'Keine passenden Typen gefunden.' : 'Noch keine Qualifikationstypen angelegt.' }}
              </p>
            </div>
          </template>
        </DataTable>
      </template>
    </Card>

    <Dialog
      v-model:visible="showForm"
      :header="editingType ? 'Qualifikationstyp bearbeiten' : 'Neuer Qualifikationstyp'"
      modal
      :style="{ width: '50vw' }"
      :breakpoints="{ '1200px': '60vw', '960px': '75vw', '640px': '95vw' }"
    >
      <QualificationTypeForm
        :typeId="editingType?.id"
        :initialData="editingType || undefined"
        @success="handleFormSuccess"
        @cancel="handleFormCancel"
      />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import type { QualificationType } from '@/types/qualifications'
import QualificationTypeForm from '@/components/qualifications/organisms/QualificationTypeForm.vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import ProgressSpinner from 'primevue/progressspinner'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { getApiErrorMessage } from '@/utils/apiError'

const router = useRouter()
const qualificationsStore = useQualificationsStore()
const toast = useToast()
const confirm = useConfirm()

const showForm = ref(false)
const editingType = ref<QualificationType | null>(null)
const typeSearch = ref('')

onMounted(async () => {
  await qualificationsStore.fetchQualificationTypes()
})

const filteredQualificationTypes = computed(() => {
  const search = typeSearch.value.trim().toLowerCase()
  if (!search) {
    return qualificationsStore.qualificationTypes
  }
  return qualificationsStore.qualificationTypes.filter((type) => {
    const haystack = `${type.name} ${type.description || ''}`.toLowerCase()
    return haystack.includes(search)
  })
})

const totalQualificationTypes = computed(() => qualificationsStore.qualificationTypes.length)
const expiringTypesCount = computed(() =>
  qualificationsStore.qualificationTypes.filter((type) => type.expires).length
)

const handleCreate = () => {
  editingType.value = null
  showForm.value = true
}

const handleEdit = (type: QualificationType) => {
  editingType.value = type
  showForm.value = true
}

const handleDelete = (type: QualificationType) => {
  confirm.require({
    message: `Möchten Sie den Qualifikationstyp "${type.name}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await qualificationsStore.deleteQualificationType(type.id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Qualifikationstyp erfolgreich gelöscht',
          life: 3000
        })
        await qualificationsStore.fetchQualificationTypes(true)
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: getApiErrorMessage(error, 'Fehler beim Löschen'),
          life: 3000
        })
      }
    }
  })
}

const handleFormSuccess = async () => {
  const wasEditing = Boolean(editingType.value)
  showForm.value = false
  editingType.value = null
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: wasEditing ? 'Qualifikationstyp aktualisiert' : 'Qualifikationstyp erstellt',
    life: 3000
  })
  await qualificationsStore.fetchQualificationTypes(true)
}

const handleFormCancel = () => {
  showForm.value = false
  editingType.value = null
}
</script>

<style scoped>
.type-management-view {
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.type-management-toolbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.name-with-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.toolbar-card {
  flex: 1 1 260px;
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.toolbar-card label {
  font-size: 0.85rem;
  color: var(--text-color-secondary);
}

.toolbar-stats {
  flex: 1 1 260px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.75rem;
}

.stat-card {
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  padding: 0.9rem 1rem;
  background: var(--surface-section);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.stat-card span {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-card strong {
  font-size: 1.5rem;
  line-height: 1;
}

.type-management-card {
  border: none;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 3rem 0;
}

.action-buttons {
  display: flex;
  gap: 0.35rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 0;
  color: var(--text-color-secondary);
  gap: 0.5rem;
}

.empty-state i {
  font-size: 1.6rem;
}

@media (max-width: 768px) {
  .type-management-view {
    padding: 1rem;
  }

  .type-management-toolbar {
    flex-direction: column;
  }

  .toolbar-stats {
    grid-template-columns: 1fr 1fr;
  }

  .type-management-card :deep(.p-card-title) {
    font-size: 1.1rem;
  }
}

@media (max-width: 480px) {
  .toolbar-stats {
    grid-template-columns: 1fr;
  }
}
</style>
