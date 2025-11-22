<template>
  <div class="qualifications-dashboard">
    <div class="dashboard-header">
      <div class="header-content">
        <h1>
          <i class="pi pi-certificate"></i>
          Qualifikationen & Sonderaufgaben
        </h1>
        <div class="header-actions">
          <Button
            label="Neue Qualifikation"
            icon="pi pi-plus"
            @click="router.push('/qualifications/create')"
          />
          <Button
            label="Neue Sonderaufgabe"
            icon="pi pi-plus"
            severity="secondary"
            @click="router.push('/qualifications/specialtasks/create')"
          />
          
          <Button
            label="Qualifikationstypen"
            icon="pi pi-cog"
            severity="help"
            outlined
            @click="router.push('/qualifications/types')"
          />
          <Button
            label="Aufgabentypen"
            icon="pi pi-cog"
            severity="help"
            outlined
            @click="router.push('/qualifications/specialtasks/types')"
          />
        </div>
      </div>
    </div>

    <!-- Statistics Cards -->
    <div v-if="!loadingStatistics && statistics" class="statistics-grid">
      <StatisticsCard
        title="Qualifikationen gesamt"
        :value="statistics.total_qualifications"
        icon="pi-certificate"
        severity="primary"
      />
      <StatisticsCard
        title="Abgelaufen"
        :value="statistics.expired_qualifications"
        icon="pi-exclamation-triangle"
        severity="danger"
      />
      <StatisticsCard
        title="Läuft bald ab"
        :value="statistics.expiring_qualifications"
        icon="pi-clock"
        severity="warning"
      />
      <StatisticsCard
        title="Aktive Aufgaben"
        :value="statistics.active_special_tasks"
        icon="pi-briefcase"
        severity="success"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loadingStatistics" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Error State -->
    <Message v-if="error && !loadingStatistics" severity="error" :closable="false">
      {{ error }}
    </Message>

    <!-- Content Tables -->
    <div v-if="!loadingStatistics && statistics" class="content-panels">
      <!-- Expiring Qualifications Table (Priority) -->
      <Panel 
        v-if="statistics.expiring_qualifications > 0"
        header="⚠️ Bald ablaufende Qualifikationen" 
        class="content-panel priority-panel"
      >
        <QualificationsTable
          ref="expiringTableRef"
          :showFilters="false"
          :showPagination="false"
          :pageSize="10"
          statusFilter="expiring"
          sortField="date_expires"
          :sortOrder="1"
          @view="router.push(`/qualifications/${$event}`)"
          @edit="router.push(`/qualifications/${$event}/edit`)"
          @delete="handleDeleteQualification"
        />
      </Panel>

      <!-- All Qualifications Table -->
      <Panel header="Alle Qualifikationen" class="content-panel">
        <template #icons>
          <Button
            label="Neue Qualifikation"
            icon="pi pi-plus"
            @click="router.push('/qualifications/create')"
          />
        </template>

        <QualificationsTable
          ref="allTableRef"
          :showFilters="true"
          :showPagination="true"
          :pageSize="20"
          statusFilter="all"
          sortField="date_expires"
          :sortOrder="1"
          @view="router.push(`/qualifications/${$event}`)"
          @edit="router.push(`/qualifications/${$event}/edit`)"
          @delete="handleDeleteQualification"
        />
      </Panel>

      <Panel header="Aktive Sonderaufgaben" class="content-panel">
        <template #icons>
          <Button
            label="Neue Sonderaufgabe"
            icon="pi pi-plus"
            severity="secondary"
            @click="router.push('/qualifications/specialtasks/create')"
          />
        </template>

        <SpecialTasksTable
          v-if="hasActiveSpecialTasks"
          :tasks="activeSpecialTasks"
          :loading="qualificationsStore.loading"
          @view="handleViewSpecialTask"
          @edit="handleEditSpecialTask"
          @delete="handleDeleteSpecialTask"
          @end="handleEndSpecialTask"
        />

        <div v-else class="empty-state special-task-empty">
          <i class="pi pi-briefcase" style="font-size: 2rem"></i>
          <p>Aktuell sind keine Sonderaufgaben aktiv.</p>
        </div>
      </Panel>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import Button from 'primevue/button'
import Panel from 'primevue/panel'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import StatisticsCard from '@/components/qualifications/molecules/StatisticsCard.vue'
import QualificationsTable from '@/components/qualifications/organisms/QualificationsTable.vue'
import SpecialTasksTable from '@/components/qualifications/organisms/SpecialTasksTable.vue'

const router = useRouter()
const qualificationsStore = useQualificationsStore()
const toast = useToast()
const confirm = useConfirm()
const expiringTableRef = ref<InstanceType<typeof QualificationsTable> | null>(null)
const allTableRef = ref<InstanceType<typeof QualificationsTable> | null>(null)

// Computed properties from store
const statistics = computed(() => qualificationsStore.statistics)
const loadingStatistics = computed(() => qualificationsStore.loadingStatistics)
const error = computed(() => qualificationsStore.error)
const activeSpecialTasks = computed(() => statistics.value?.active_special_tasks_list ?? [])
const hasActiveSpecialTasks = computed(() => activeSpecialTasks.value.length > 0)

async function refreshStatistics() {
  try {
    await qualificationsStore.fetchStatistics()
  } catch (e) {
    console.error('Failed to refresh statistics:', e)
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Aktualisierte Statistiken konnten nicht geladen werden.',
      life: 4000
    })
  }
}

function handleDeleteQualification(id: number) {
  confirm.require({
    message: 'Soll diese Qualifikation wirklich gelöscht werden?',
    header: 'Qualifikation löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await qualificationsStore.deleteQualification(id)
        await refreshStatistics()
        await expiringTableRef.value?.reload(true)
        await allTableRef.value?.reload(true)
        toast.add({
          severity: 'success',
          summary: 'Qualifikation gelöscht',
          detail: 'Die Qualifikation wurde entfernt.',
          life: 3000
        })
      } catch (error: any) {
        console.error('Failed to delete qualification:', error)
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: error?.message || 'Qualifikation konnte nicht gelöscht werden.',
          life: 4000
        })
      }
    }
  })
}

function handleViewSpecialTask(id: number) {
  router.push(`/qualifications/specialtasks/${id}`)
}

function handleEditSpecialTask(id: number) {
  router.push(`/qualifications/specialtasks/${id}/edit`)
}

function handleEndSpecialTask(id: number) {
  confirm.require({
    message: 'Möchtest du diese Sonderaufgabe wirklich beenden?',
    header: 'Sonderaufgabe beenden',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Beenden',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-warning',
    accept: async () => {
      try {
        await qualificationsStore.endSpecialTask(id)
        await refreshStatistics()
        toast.add({
          severity: 'success',
          summary: 'Sonderaufgabe beendet',
          detail: 'Die Sonderaufgabe wurde erfolgreich beendet.',
          life: 3000
        })
      } catch (error: any) {
        console.error('Failed to end special task:', error)
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: error?.message || 'Sonderaufgabe konnte nicht beendet werden.',
          life: 4000
        })
      }
    }
  })
}

function handleDeleteSpecialTask(id: number) {
  confirm.require({
    message: 'Soll diese Sonderaufgabe dauerhaft gelöscht werden?',
    header: 'Sonderaufgabe löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await qualificationsStore.deleteSpecialTask(id)
        await refreshStatistics()
        toast.add({
          severity: 'success',
          summary: 'Sonderaufgabe gelöscht',
          detail: 'Die Sonderaufgabe wurde entfernt.',
          life: 3000
        })
      } catch (error: any) {
        console.error('Failed to delete special task:', error)
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: error?.message || 'Sonderaufgabe konnte nicht gelöscht werden.',
          life: 4000
        })
      }
    }
  })
}

// Lifecycle
onMounted(async () => {
  try {
    await qualificationsStore.fetchStatistics()
  } catch (e) {
    console.error('Failed to load dashboard:', e)
  }
})
</script>

<style scoped>
.qualifications-dashboard {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.dashboard-header {
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.header-content h1 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1.75rem;
  color: var(--text-color);
}

.header-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.content-panels {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.content-panel {
  width: 100%;
}

.priority-panel {
  border-left: 4px solid var(--orange-500);
}

.special-task-empty {
  text-align: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  color: var(--text-color-secondary);
  gap: 1rem;
}

.empty-state p {
  margin: 0;
  font-size: 1.125rem;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 4rem;
}

@media (max-width: 768px) {
  .qualifications-dashboard {
    padding: 1rem;
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;
  }

  .header-content h1 {
    font-size: 1.5rem;
  }

  .header-actions {
    flex-direction: column;
  }

  .header-actions :deep(.p-button) {
    width: 100%;
  }

  .statistics-grid {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .cards-grid {
    grid-template-columns: 1fr;
  }
}
</style>
