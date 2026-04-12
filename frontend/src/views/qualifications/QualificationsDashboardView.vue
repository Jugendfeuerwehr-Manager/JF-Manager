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

    <section v-if="isMobile" class="mobile-qualifications-section">
      <TabView v-model:activeIndex="mobileTabIndex" class="mobile-tabview">
        <TabPanel header="Qualifikationen" value="0">
          <div class="mobile-tab-content">
            <Card class="mobile-filter-card">
              <template #content>
                <div class="mobile-filter-grid">
                  <div class="mobile-filter-field">
                    <label for="qual-mobile-search">Suche</label>
                    <InputText
                      id="qual-mobile-search"
                      v-model="mobileFilters.search"
                      placeholder="Person oder Typ"
                    />
                  </div>
                  <div class="mobile-filter-field">
                    <label for="qual-mobile-status">Status</label>
                    <Dropdown
                      id="qual-mobile-status"
                      v-model="mobileFilters.status"
                      :options="mobileQualificationStatusOptions"
                      optionLabel="label"
                      optionValue="value"
                    />
                  </div>
                  <div class="mobile-filter-field">
                    <label for="qual-mobile-type">Typ</label>
                    <Dropdown
                      id="qual-mobile-type"
                      v-model="mobileFilters.type"
                      :options="qualificationTypeOptions"
                      optionLabel="label"
                      optionValue="value"
                      showClear
                    />
                  </div>
                </div>
              </template>
            </Card>

            <QualificationsMobileList
              :items="mobileQualifications"
              :loading="mobileQualificationListLoading"
              :rows="mobilePageSize"
              :total-records="mobileTotalRecords"
              @page-change="handleMobilePageChange"
              @view="router.push(`/qualifications/${$event}`)"
              @edit="router.push(`/qualifications/${$event}/edit`)"
              @delete="handleDeleteQualification"
            />
          </div>
        </TabPanel>

        <TabPanel header="Sonderaufgaben" value="1">
          <div class="mobile-tab-content">
            <Card class="mobile-filter-card">
              <template #content>
                <div class="mobile-filter-grid">
                  <div class="mobile-filter-field">
                    <label for="special-mobile-search">Suche</label>
                    <InputText
                      id="special-mobile-search"
                      v-model="mobileSpecialTaskFilters.search"
                      placeholder="Person oder Aufgabe"
                    />
                  </div>
                  <div class="mobile-filter-field">
                    <label for="special-mobile-status">Status</label>
                    <Dropdown
                      id="special-mobile-status"
                      v-model="mobileSpecialTaskFilters.status"
                      :options="mobileSpecialTaskStatusOptions"
                      optionLabel="label"
                      optionValue="value"
                    />
                  </div>
                  <div class="mobile-filter-field">
                    <label for="special-mobile-type">Aufgabentyp</label>
                    <Dropdown
                      id="special-mobile-type"
                      v-model="mobileSpecialTaskFilters.task"
                      :options="specialTaskTypeOptions"
                      optionLabel="label"
                      optionValue="value"
                      showClear
                    />
                  </div>
                </div>
              </template>
            </Card>

            <SpecialTasksMobileList
              :items="mobileSpecialTasks"
              :loading="mobileSpecialTaskListLoading"
              :rows="mobileSpecialTaskPageSize"
              :total-records="mobileSpecialTaskTotalRecords"
              @page-change="handleMobileSpecialTaskPageChange"
              @view="handleViewSpecialTask"
              @edit="handleEditSpecialTask"
              @end="handleEndSpecialTask"
              @delete="handleDeleteSpecialTask"
            />
          </div>
        </TabPanel>
      </TabView>
    </section>

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
    <div v-else-if="!loadingStatistics && statistics" class="content-panels">
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
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQualificationsStore } from '@/stores/qualifications'
import Button from 'primevue/button'
import Panel from 'primevue/panel'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import Dropdown from 'primevue/dropdown'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import StatisticsCard from '@/components/qualifications/molecules/StatisticsCard.vue'
import QualificationsTable from '@/components/qualifications/organisms/QualificationsTable.vue'
import SpecialTasksTable from '@/components/qualifications/organisms/SpecialTasksTable.vue'
import QualificationsMobileList from '@/components/qualifications/organisms/QualificationsMobileList.vue'
import SpecialTasksMobileList from '@/components/qualifications/organisms/SpecialTasksMobileList.vue'
import type { QualificationListParams, SpecialTaskListParams } from '@/types/qualifications'

const router = useRouter()
const qualificationsStore = useQualificationsStore()
const toast = useToast()
const confirm = useConfirm()
const expiringTableRef = ref<InstanceType<typeof QualificationsTable> | null>(null)
const allTableRef = ref<InstanceType<typeof QualificationsTable> | null>(null)
const isMobile = ref(window.innerWidth < 768)
const mobilePage = ref(1)
const mobilePageSize = ref(10)
const mobileLoading = ref(false)
const mobileFilters = reactive({
  search: '',
  status: 'all' as QualificationListParams['status'],
  type: null as number | null
})
const mobileTabIndex = ref(0)
const mobileSpecialTaskPage = ref(1)
const mobileSpecialTaskPageSize = ref(10)
const mobileSpecialTaskLoading = ref(false)
const mobileSpecialTaskFilters = reactive({
  search: '',
  status: 'active' as SpecialTaskListParams['status'],
  task: null as number | null
})

// Computed properties from store
const statistics = computed(() => qualificationsStore.statistics)
const loadingStatistics = computed(() => qualificationsStore.loadingStatistics)
const error = computed(() => qualificationsStore.error)
const activeSpecialTasks = computed(() => statistics.value?.active_special_tasks_list ?? [])
const hasActiveSpecialTasks = computed(() => activeSpecialTasks.value.length > 0)
let mobileSearchTimeout: ReturnType<typeof setTimeout> | null = null
let mobileSpecialTaskSearchTimeout: ReturnType<typeof setTimeout> | null = null

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
}

const loadMobileQualifications = async () => {
  if (!isMobile.value) return
  mobileLoading.value = true
  try {
    await qualificationsStore.fetchQualifications({
      page: mobilePage.value,
      page_size: mobilePageSize.value,
      search: mobileFilters.search || undefined,
      status: mobileFilters.status !== 'all' ? mobileFilters.status : undefined,
      type: mobileFilters.type || undefined,
      ordering: 'date_expires'
    })
  } catch {
  } finally {
    mobileLoading.value = false
  }
}

const loadMobileSpecialTasks = async () => {
  if (!isMobile.value) return
  mobileSpecialTaskLoading.value = true
  try {
    await qualificationsStore.fetchSpecialTasks({
      page: mobileSpecialTaskPage.value,
      page_size: mobileSpecialTaskPageSize.value,
      search: mobileSpecialTaskFilters.search || undefined,
      status:
        mobileSpecialTaskFilters.status !== 'all'
          ? mobileSpecialTaskFilters.status
          : undefined,
      task: mobileSpecialTaskFilters.task || undefined,
      ordering: '-start_date'
    })
  } catch {
  } finally {
    mobileSpecialTaskLoading.value = false
  }
}

const handleMobilePageChange = async (page: number, size: number) => {
  mobilePage.value = page
  mobilePageSize.value = size
  await loadMobileQualifications()
}

const handleMobileSpecialTaskPageChange = async (page: number, size: number) => {
  mobileSpecialTaskPage.value = page
  mobileSpecialTaskPageSize.value = size
  await loadMobileSpecialTasks()
}

watch(isMobile, (value) => {
  if (value) {
    mobilePage.value = 1
    loadMobileQualifications()
    if (mobileTabIndex.value === 1) {
      mobileSpecialTaskPage.value = 1
      loadMobileSpecialTasks()
    }
  }
})

watch(mobileTabIndex, (index) => {
  if (!isMobile.value) return
  if (index === 0) {
    mobilePage.value = 1
    loadMobileQualifications()
  } else {
    mobileSpecialTaskPage.value = 1
    loadMobileSpecialTasks()
  }
})

watch(
  () => [mobileFilters.status, mobileFilters.type],
  () => {
    if (!isMobile.value || mobileTabIndex.value !== 0) return
    mobilePage.value = 1
    loadMobileQualifications()
  }
)

watch(
  () => mobileFilters.search,
  () => {
    if (!isMobile.value || mobileTabIndex.value !== 0) return
    if (mobileSearchTimeout) {
      clearTimeout(mobileSearchTimeout)
    }
    mobileSearchTimeout = setTimeout(() => {
      mobilePage.value = 1
      loadMobileQualifications()
    }, 350)
  }
)

watch(
  () => [mobileSpecialTaskFilters.status, mobileSpecialTaskFilters.task],
  () => {
    if (!isMobile.value || mobileTabIndex.value !== 1) return
    mobileSpecialTaskPage.value = 1
    loadMobileSpecialTasks()
  }
)

watch(
  () => mobileSpecialTaskFilters.search,
  () => {
    if (!isMobile.value || mobileTabIndex.value !== 1) return
    if (mobileSpecialTaskSearchTimeout) {
      clearTimeout(mobileSpecialTaskSearchTimeout)
    }
    mobileSpecialTaskSearchTimeout = setTimeout(() => {
      mobileSpecialTaskPage.value = 1
      loadMobileSpecialTasks()
    }, 350)
  }
)
const mobileQualifications = computed(() => qualificationsStore.qualifications)
const mobileTotalRecords = computed(() => qualificationsStore.qualificationsTotal)
const qualificationTypeOptions = computed(() => [
  { label: 'Alle Typen', value: null },
  ...qualificationsStore.qualificationTypes.map((type) => ({
    label: type.name,
    value: type.id
  }))
])
const specialTaskTypeOptions = computed(() => [
  { label: 'Alle Aufgaben', value: null },
  ...qualificationsStore.specialTaskTypes.map((type) => ({
    label: type.name,
    value: type.id
  }))
])
const mobileQualificationStatusOptions = [
  { label: 'Alle', value: 'all' },
  { label: 'Gültig', value: 'active' },
  { label: 'Läuft bald ab', value: 'expiring' },
  { label: 'Abgelaufen', value: 'expired' }
]
const mobileSpecialTaskStatusOptions = [
  { label: 'Alle', value: 'all' },
  { label: 'Aktiv', value: 'active' },
  { label: 'Beendet', value: 'ended' }
]
const mobileQualificationListLoading = computed(
  () => mobileLoading.value || qualificationsStore.loading
)
const mobileSpecialTasks = computed(() => qualificationsStore.specialTasks)
const mobileSpecialTaskTotalRecords = computed(() => qualificationsStore.specialTasksTotal)
const mobileSpecialTaskListLoading = computed(
  () => mobileSpecialTaskLoading.value || qualificationsStore.loading
)

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
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Qualifikation konnte nicht gelöscht werden.',
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
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Sonderaufgabe konnte nicht beendet werden.',
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
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Sonderaufgabe konnte nicht gelöscht werden.',
          life: 4000
        })
      }
    }
  })
}

// Lifecycle
onMounted(async () => {
  window.addEventListener('resize', handleResize)
  try {
    await Promise.all([
      qualificationsStore.fetchStatistics(),
      qualificationsStore.fetchQualificationTypes(),
      qualificationsStore.fetchSpecialTaskTypes()
    ])
    if (isMobile.value) {
      if (mobileTabIndex.value === 0) {
        await loadMobileQualifications()
      } else {
        await loadMobileSpecialTasks()
      }
    }
  } catch (e) {
    console.error('Failed to load dashboard:', e)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (mobileSearchTimeout) {
    clearTimeout(mobileSearchTimeout)
  }
  if (mobileSpecialTaskSearchTimeout) {
    clearTimeout(mobileSpecialTaskSearchTimeout)
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

.mobile-filter-card {
  margin-bottom: 1rem;
}

.mobile-filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}

.mobile-filter-field label {
  display: block;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-bottom: 0.25rem;
}

.mobile-qualifications-section {
  margin-top: 1rem;
}

.mobile-tab-content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.mobile-tabview :deep(.p-tabview-nav) {
  border-bottom: none;
  gap: 0.5rem;
}

.mobile-tabview :deep(.p-tabview-nav li .p-tabview-nav-link) {
  border-radius: var(--border-radius);
  border: 1px solid var(--surface-border);
  background: var(--surface-card);
}

.mobile-tabview :deep(.p-tabview-nav li.p-highlight .p-tabview-nav-link) {
  border-color: var(--primary-color);
  color: var(--primary-color);
}

.mobile-tabview :deep(.p-tabview-panels) {
  background: transparent;
  padding: 0;
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
