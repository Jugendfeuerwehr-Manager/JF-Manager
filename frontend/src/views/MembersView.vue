<template>
  <div class="members-view">
    <OverviewHeader
      title="Mitglieder"
      subtitle="Verwaltung der Jugendfeuerwehr-Mitglieder"
    >
      <template #actions>
        <Button
          label="Excel-Export"
          icon="pi pi-file-excel"
          @click="handleExportExcel"
          severity="success"
          outlined
          :loading="membersStore.loading"
        />
        <Button
          label="Mitglied hinzufügen"
          icon="pi pi-plus"
          @click="navigateToCreate"
          severity="primary"
        />
      </template>
    </OverviewHeader>

    <Card class="filter-card">
      <template #content>
        <div class="filter-grid">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText
              v-model="filters.search"
              placeholder="Suchen..."
              class="w-full"
              @input="onFilterChange"
            />
          </IconField>
          
          <Dropdown
            v-model="filters.status"
            :options="membersStore.statuses || []"
            option-label="name"
            option-value="id"
            placeholder="Status filtern"
            show-clear
            class="w-full"
            @change="onFilterChange"
          />
          
          <Dropdown
            v-model="filters.group"
            :options="membersStore.groups || []"
            option-label="name"
            option-value="id"
            placeholder="Gruppe filtern"
            show-clear
            class="w-full"
            @change="onFilterChange"
          />

          <Dropdown
            v-model="filters.gender"
            :options="genderFilterOptions"
            option-label="label"
            option-value="value"
            placeholder="Geschlecht filtern"
            show-clear
            class="w-full"
            @change="onFilterChange"
          />
        </div>
      </template>
    </Card>

    <!-- Statistics Panel (collapsible) -->
    <div class="stats-panel">
      <div class="stats-panel__header" @click="toggleStats">
        <span class="stats-panel__title">
          <i class="pi pi-chart-bar"></i>
          Statistiken
          <Tag :value="`${membersStore.pagination.count} Mitglieder`" severity="secondary" class="ml-2" />
        </span>
        <i :class="['pi', statsExpanded ? 'pi-chevron-up' : 'pi-chevron-down']"></i>
      </div>

      <Transition name="stats-slide">
        <div v-if="statsExpanded" class="stats-panel__content">
          <div v-if="statsLoading" class="stats-loading">
            <i class="pi pi-spin pi-spinner"></i>
            <span>Statistiken werden geladen...</span>
          </div>
          <div v-else-if="stats" class="stats-grid">

            <!-- Gender -->
            <div class="stat-card">
              <div class="stat-card__title">
                <i class="pi pi-users"></i>
                Geschlecht
              </div>
              <div class="stat-bar-group">
                <div v-for="g in genderStats" :key="g.label" class="stat-bar-row">
                  <span class="stat-bar-label">{{ g.label }}</span>
                  <div class="stat-bar-track">
                    <div
                      class="stat-bar-fill"
                      :style="{ width: stats.total ? `${(g.value / stats.total) * 100}%` : '0%', backgroundColor: g.color }"
                    ></div>
                  </div>
                  <span class="stat-bar-value">{{ g.value }}</span>
                </div>
              </div>
            </div>

            <!-- Age -->
            <div class="stat-card">
              <div class="stat-card__title">
                <i class="pi pi-calendar"></i>
                Alter
              </div>
              <div v-if="stats.age && stats.age.avg != null" class="age-overview">
                <div class="age-kpis">
                  <div class="age-kpi">
                    <span class="age-kpi__value">{{ stats.age.avg }}</span>
                    <span class="age-kpi__label">Ø Jahre</span>
                  </div>
                  <div class="age-kpi">
                    <span class="age-kpi__value">{{ stats.age.min }}</span>
                    <span class="age-kpi__label">Jüngste/r</span>
                  </div>
                  <div class="age-kpi">
                    <span class="age-kpi__value">{{ stats.age.max }}</span>
                    <span class="age-kpi__label">Älteste/r</span>
                  </div>
                </div>
                <div class="stat-bar-group mt-2">
                  <div v-for="bucket in stats.age.buckets" :key="bucket.label" class="stat-bar-row">
                    <span class="stat-bar-label">{{ bucket.label }}</span>
                    <div class="stat-bar-track">
                      <div
                        class="stat-bar-fill"
                        :style="{ width: stats.total ? `${(bucket.count / stats.total) * 100}%` : '0%', backgroundColor: '#4facfe' }"
                      ></div>
                    </div>
                    <span class="stat-bar-value">{{ bucket.count }}</span>
                  </div>
                </div>
              </div>
              <p v-else class="stats-empty">Keine Geburtstagsdaten vorhanden</p>
            </div>

            <!-- Status -->
            <div class="stat-card">
              <div class="stat-card__title">
                <i class="pi pi-tag"></i>
                Status
              </div>
              <div class="stat-bar-group">
                <div v-for="s in stats.by_status" :key="s.name" class="stat-bar-row">
                  <span class="stat-bar-label">{{ s.name }}</span>
                  <div class="stat-bar-track">
                    <div
                      class="stat-bar-fill"
                      :style="{ width: stats.total ? `${(s.count / stats.total) * 100}%` : '0%', backgroundColor: s.color }"
                    ></div>
                  </div>
                  <span class="stat-bar-value">{{ s.count }}</span>
                </div>
              </div>
            </div>

            <!-- Misc -->
            <div class="stat-card">
              <div class="stat-card__title">
                <i class="pi pi-info-circle"></i>
                Sonstiges
              </div>
              <div class="misc-stats">
                <div class="misc-stat-row">
                  <span class="misc-stat-label">
                    <i class="pi pi-check-circle" style="color: #43e97b"></i>
                    Kann schwimmen
                  </span>
                  <span class="misc-stat-value">
                    {{ stats.can_swim }}
                    <span class="misc-stat-pct">
                      ({{ stats.total ? Math.round((stats.can_swim / stats.total) * 100) : 0 }} %)
                    </span>
                  </span>
                </div>
                <div v-for="g in stats.by_group" :key="g.name" class="misc-stat-row">
                  <span class="misc-stat-label">
                    <i class="pi pi-users"></i>
                    {{ g.name }}
                  </span>
                  <span class="misc-stat-value">{{ g.count }}</span>
                </div>
              </div>
            </div>

          </div>
        </div>
      </Transition>
    </div>

    <!-- Desktop Table View -->
    <Card class="table-card desktop-view">
      <template #content>
        <DataTable
          v-model:filters="lazyParams.filters"
          :value="membersStore.members"
          :lazy="true"
          :paginator="true"
          :rows="lazyParams.rows"
          :first="lazyParams.first"
          :total-records="membersStore.pagination.count"
          :loading="membersStore.loading"
          :rows-per-page-options="[10, 20, 50]"
          paginator-template="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
          current-page-report-template="{first} bis {last} von {totalRecords}"
          striped-rows
          removable-sort
          @page="onPage"
          @sort="onSort"
          @row-click="onRowClick"
          class="clickable-rows"
        >
          <Column :style="{ width: '3rem' }">
            <template #body="{ data }">
              <i
                v-if="data.has_alert"
                class="pi pi-exclamation-triangle alert-icon"
                v-tooltip.top="'Anwesenheitsalarm'"
              />
            </template>
          </Column>

          <Column 
            field="name" 
            header="Vorname" 
            sortable
          />
          
          <Column 
            field="lastname" 
            header="Nachname" 
            sortable
          />
          
          <Column 
            field="birthday" 
            header="Geburtstag" 
            sortable
          >
            <template #body="{ data }">
              {{ formatDate(data.birthday) }} ({{ data.age }})
            </template>
          </Column>
        
          
          <Column 
            field="status" 
            header="Status"
          >
            <template #body="{ data }">
              <Tag 
                v-if="data.status"
                :value="data.status.name"
                :style="{ backgroundColor: data.status.color, color: 'white' }"
              />
            </template>
          </Column>
          
          <Column header="Aktionen" :style="{ width: '12rem' }">
            <template #body="{ data }">
              <div class="action-buttons">
                <Button
                  icon="pi pi-eye"
                  size="small"
                  text
                  rounded
                  @click="navigateToView(data)"
                  :title="'Ansehen'"
                />
                <Button
                  icon="pi pi-pencil"
                  size="small"
                  text
                  rounded
                  severity="secondary"
                  @click="navigateToEdit(data)"
                  :title="'Bearbeiten'"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  text
                  rounded
                  severity="danger"
                  @click="confirmDelete(data)"
                  :title="'Löschen'"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Mobile Card View -->
    <div class="mobile-view">
      <ResponsiveList
        :items="membersStore.members"
        :loading="membersStore.loading"
        :rows="lazyParams.rows"
        :paginator="membersStore.pagination.count > lazyParams.rows"
        :total-records="membersStore.pagination.count"
        :lazy="true"
        item-key="id"
        @page="onPage"
      >
        <template #item="{ item: member }">
          <Card
            class="member-card mobile-entity-card"
            @click="navigateToView(member)"
          >
            <template #content>
              <div class="mobile-entity-card__header">
                <div>
                  <h3 class="mobile-entity-card__title">{{ member.full_name }}</h3>
                  <p class="mobile-entity-card__meta">
                    {{ formatDate(member.birthday) }} · {{ member.age }} Jahre
                  </p>
                </div>
                <Tag
                  v-if="member.status"
                  :value="member.status.name"
                  :style="{ backgroundColor: member.status.color, color: 'white' }"
                />
              </div>

              <div class="mobile-entity-card__section">
                <div class="mobile-entity-card__row">
                  <span class="mobile-entity-card__label">
                    <i class="pi pi-calendar"></i>
                    Geburtstag
                  </span>
                  <span class="mobile-entity-card__value">
                    {{ formatDate(member.birthday) }} ({{ member.age }})
                  </span>
                </div>
              </div>

              <ParentContacts :member="member" variant="compact" />

              <div class="mobile-entity-card__actions" @click.stop>
                <Button
                  label="Ansehen"
                  icon="pi pi-eye"
                  size="small"
                  outlined
                  @click="navigateToView(member)"
                />
                <Button
                  label="Bearbeiten"
                  icon="pi pi-pencil"
                  size="small"
                  outlined
                  severity="secondary"
                  @click="navigateToEdit(member)"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  outlined
                  severity="danger"
                  @click="confirmDelete(member)"
                />
              </div>
            </template>
          </Card>
        </template>

        <template #empty>
          <div class="mobile-list-empty">
            <i class="pi pi-users"></i>
            <p>Keine Mitglieder gefunden</p>
          </div>
        </template>
      </ResponsiveList>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useMembersStore } from '@/stores/members'
import { membersApi, parentsApi } from '@/api/members'
import type { Member, Parent } from '@/types/api'
import { useQueryTableState } from '@/composables/useQueryTableState'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Tag from 'primevue/tag'
import Dialog from 'primevue/dialog'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import ParentContacts from '@/components/members/ParentContacts.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'

const router = useRouter()
const membersStore = useMembersStore()
const confirm = useConfirm()
const toast = useToast()
const { getInt, getString, syncToUrl } = useQueryTableState()

// Contact dialog
const showContactDialog = ref(false)
const selectedParent = ref<Parent | null>(null)

onUnmounted(() => {
  
})

const filters = reactive({
  search: getString('search'),
  status: getInt('status', 0) || null as number | null,
  group: getInt('group', 0) || null as number | null,
  gender: getString('gender') as string,
})

const genderFilterOptions = [
  { label: 'Männlich', value: 'male' },
  { label: 'Weiblich', value: 'female' },
  { label: 'Divers', value: 'diverse' },
]

// Statistics
const statsExpanded = ref(false)
const statsLoading = ref(false)
const stats = ref<any>(null)

const genderStats = computed(() => {
  if (!stats.value) return []
  const g = stats.value.gender
  return [
    { label: 'Männlich', value: g?.male ?? 0, color: '#4facfe' },
    { label: 'Weiblich', value: g?.female ?? 0, color: '#f093fb' },
    { label: 'Divers', value: g?.diverse ?? 0, color: '#43e97b' },
    { label: 'Unbekannt', value: g?.unknown ?? 0, color: '#aaaaaa' },
  ].filter(e => e.value > 0)
})

const loadStats = async () => {
  if (stats.value) return
  statsLoading.value = true
  try {
    const response = await membersApi.getStatistics()
    stats.value = response.data
  } catch {
    stats.value = null
  } finally {
    statsLoading.value = false
  }
}

const toggleStats = async () => {
  statsExpanded.value = !statsExpanded.value
  if (statsExpanded.value && !stats.value) {
    await loadStats()
  }
}

const lazyParams = reactive({
  first: getInt('offset', 0),
  rows: getInt('rows', 20),
  sortField: getString('sortField', 'lastname'),
  sortOrder: getInt('sortOrder', 1) as 1 | -1,
  filters: {}
})

const MEMBERS_URL_DEFAULTS = { offset: 0, rows: 20, sortField: 'lastname', sortOrder: 1 }

let filterTimeout: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  await Promise.all([
    membersStore.fetchStatuses(),
    membersStore.fetchGroups()
  ])
  loadLazyData()
})

const loadLazyData = () => {
  const offset = lazyParams.first
  const limit = lazyParams.rows
  
  let ordering = ''
  if (lazyParams.sortField) {
    ordering = lazyParams.sortOrder === -1 ? `-${lazyParams.sortField}` : lazyParams.sortField
  }

  membersStore.fetchMembers({
    offset,
    limit,
    search: filters.search || undefined,
    status: filters.status || undefined,
    group: filters.group || undefined,
    gender: filters.gender || undefined,
    ordering: ordering || undefined
  })
}

const onPage = (event: any) => {
  lazyParams.first = event.first
  lazyParams.rows = event.rows
  syncToUrl({ search: filters.search, status: filters.status, group: filters.group, gender: filters.gender, offset: lazyParams.first, rows: lazyParams.rows, sortField: lazyParams.sortField, sortOrder: lazyParams.sortOrder }, MEMBERS_URL_DEFAULTS)
  loadLazyData()
}

const onSort = (event: any) => {
  lazyParams.sortField = event.sortField
  lazyParams.sortOrder = event.sortOrder
  syncToUrl({ search: filters.search, status: filters.status, group: filters.group, gender: filters.gender, offset: lazyParams.first, rows: lazyParams.rows, sortField: lazyParams.sortField, sortOrder: lazyParams.sortOrder }, MEMBERS_URL_DEFAULTS)
  loadLazyData()
}

const onFilterChange = () => {
  if (filterTimeout) {
    clearTimeout(filterTimeout)
  }
  filterTimeout = setTimeout(() => {
    lazyParams.first = 0
    syncToUrl({ search: filters.search, status: filters.status, group: filters.group, gender: filters.gender, offset: lazyParams.first, rows: lazyParams.rows, sortField: lazyParams.sortField, sortOrder: lazyParams.sortOrder }, MEMBERS_URL_DEFAULTS)
    loadLazyData()
  }, 500)
}

const formatDate = (dateString: string | null) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const navigateToCreate = () => {
  router.push('/members/create')
}

const navigateToView = (member: Member) => {
  router.push(`/members/${member.id}`)
}

const navigateToEdit = (member: Member) => {
  router.push(`/members/${member.id}/edit`)
}

const onRowClick = (event: any) => {
  // Navigate to member detail when row is clicked
  const member = event.data as Member
  router.push(`/members/${member.id}`)
}

const confirmDelete = (member: Member) => {
  // Identify parents that would become childless after this deletion
  const orphanedParents = (member.parents || []).filter(
    (p) => p.children.length === 1 && p.children[0] === member.id
  )

  confirm.require({
    message: `Möchten Sie ${member.full_name} wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja, löschen',
    rejectLabel: 'Abbrechen',
    acceptClass: 'p-button-danger',
    accept: async () => {
      try {
        await membersStore.deleteMember(member.id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Mitglied wurde gelöscht',
          life: 3000
        })
        loadLazyData()

        if (orphanedParents.length > 0) {
          const parentNames = orphanedParents.map((p) => p.full_name).join(', ')
          confirm.require({
            message: `${orphanedParents.length === 1 ? 'Der folgende Elternteil hat' : 'Die folgenden Elternteile haben'} nun kein verknüpftes Mitglied mehr: ${parentNames}. Möchten Sie ${orphanedParents.length === 1 ? 'diesen' : 'diese'} ebenfalls löschen?`,
            header: 'Eltern ohne Kind',
            icon: 'pi pi-exclamation-triangle',
            acceptLabel: 'Ja, löschen',
            rejectLabel: 'Behalten',
            accept: async () => {
              try {
                await Promise.all(orphanedParents.map((p) => parentsApi.delete(p.id)))
                toast.add({
                  severity: 'success',
                  summary: 'Eltern gelöscht',
                  detail: `${orphanedParents.length === 1 ? 'Elternteil wurde' : 'Elternteile wurden'} gelöscht`,
                  life: 3000
                })
              } catch {
                toast.add({
                  severity: 'error',
                  summary: 'Fehler',
                  detail: 'Elternteile konnten nicht gelöscht werden',
                  life: 3000
                })
              }
            }
          })
        }
      } catch (error) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Mitglied konnte nicht gelöscht werden',
          life: 3000
        })
      }
    }
  })
}

const handleExportExcel = async () => {
  try {
    await membersStore.exportExcel()
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Mitgliederliste wurde erfolgreich exportiert',
      life: 3000
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Export fehlgeschlagen',
      life: 3000
    })
  }
}

</script>

<style scoped>
.members-view {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.filter-card {
  margin-bottom: 1.5rem;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.table-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.alert-icon {
  color: var(--orange-500);
  font-size: 1rem;
}

/* Clickable rows styling */
.clickable-rows :deep(tbody tr) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.clickable-rows :deep(tbody tr:hover) {
  background-color: var(--surface-hover) !important;
}

/* Mobile/Desktop view toggle */
.mobile-view {
  display: none;
}

.desktop-view {
  display: block;
}

.member-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.member-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.12);
}

/* Statistics panel */
.stats-panel {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.stats-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.15s;
}

.stats-panel__header:hover {
  background: var(--surface-hover);
}

.stats-panel__title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color);
}

.stats-panel__content {
  padding: 1rem 1.25rem 1.25rem;
  border-top: 1px solid var(--surface-border);
}

.stats-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--text-color-secondary);
  padding: 1rem 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.25rem;
}

.stat-card {
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stat-card__title {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-bar-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 32px;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.stat-bar-label {
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-bar-track {
  background: var(--surface-border);
  border-radius: 4px;
  height: 8px;
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
  min-width: 2px;
}

.stat-bar-value {
  font-weight: 600;
  color: var(--text-color);
  text-align: right;
  font-size: 0.85rem;
}

/* Age KPIs */
.age-overview {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.age-kpis {
  display: flex;
  gap: 1rem;
}

.age-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  background: var(--surface-card);
  border-radius: var(--border-radius);
  padding: 0.5rem;
}

.age-kpi__value {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--primary-color);
  line-height: 1;
}

.age-kpi__label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.2rem;
}

/* Misc stats */
.misc-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.misc-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.misc-stat-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-color);
}

.misc-stat-value {
  font-weight: 600;
  color: var(--text-color);
}

.misc-stat-pct {
  font-weight: 400;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}

.stats-empty {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  margin: 0;
}

.mt-2 { margin-top: 0.5rem; }
.ml-2 { margin-left: 0.5rem; }

/* Animate stats panel open/close */
.stats-slide-enter-active,
.stats-slide-leave-active {
  transition: max-height 0.3s ease, opacity 0.2s ease;
  max-height: 800px;
  overflow: hidden;
}
.stats-slide-enter-from,
.stats-slide-leave-to {
  max-height: 0;
  opacity: 0;
}

@media (max-width: 768px) {
  .members-view {
    padding: 1rem;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  /* Hide desktop table on mobile */
  .desktop-view {
    display: none;
  }

  /* Show mobile cards on mobile */
  .mobile-view {
    display: block;
  }
}
</style>
