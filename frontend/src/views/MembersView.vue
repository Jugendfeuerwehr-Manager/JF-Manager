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
          @click="showExportDialog = true"
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
          <div class="filter-search-wrap" :class="{ 'filter-search-wrap--active': isMobileSearchMode }">
            <IconField class="filter-search-field">
              <InputIcon class="pi pi-search" />
              <InputText
                v-model="filters.search"
                placeholder="Suchen..."
                class="w-full filter-control"
                @focus="onSearchFocus"
                @input="onFilterChange"
                @keydown.esc="closeMobileSearch"
              />
            </IconField>
          </div>
          
          <Dropdown
            v-if="!isMobileSearchMode"
            v-model="filters.status"
            :options="membersStore.statuses || []"
            option-label="name"
            option-value="id"
            placeholder="Status filtern"
            show-clear
            class="w-full filter-control"
            @change="onFilterChange"
          />
          
          <Dropdown
            v-if="!isMobileSearchMode"
            v-model="filters.group"
            :options="membersStore.groups || []"
            option-label="name"
            option-value="id"
            placeholder="Gruppe filtern"
            show-clear
            class="w-full filter-control"
            @change="onFilterChange"
          />

          <Dropdown
            v-if="!isMobileSearchMode"
            v-model="filters.gender"
            :options="genderFilterOptions"
            option-label="label"
            option-value="value"
            placeholder="Geschlecht filtern"
            show-clear
            class="w-full filter-control"
            @change="onFilterChange"
          />
        </div>
      </template>
    </Card>

    <!-- Statistics Panel (collapsible) -->
    <div v-if="!isMobileSearchMode" class="stats-panel">
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
                        :style="{ width: stats.total ? `${((bucket.count ?? 0) / stats.total) * 100}%` : '0%', backgroundColor: '#4facfe' }"
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
    <Card v-if="!isMobileSearchMode" class="table-card desktop-view">
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

          <Column
            v-if="departmentsStore.isAllDepartments && departmentsStore.departments.length > 1"
            header="Abteilung"
          >
            <template #body="{ data }">
              <div class="dept-badges">
                <DepartmentBadge
                  v-for="deptId in data.department_ids"
                  :key="deptId"
                  :department="departmentsStore.departments.find((d) => d.id === deptId) ?? null"
                />
              </div>
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
    <div v-if="!isMobileSearchMode" class="mobile-view">
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

              <ParentContacts :member="member" variant="compact" />

              <div class="mobile-entity-card__actions" @click.stop>
                <Button
                  label="Ansehen"
                  icon="pi pi-eye"
                  size="small"
                  outlined
                  class="member-card-action"
                  aria-label="Mitglied ansehen"
                  @click="navigateToView(member)"
                />
                <Button
                  label="Bearbeiten"
                  icon="pi pi-pencil"
                  size="small"
                  outlined
                  severity="secondary"
                  class="member-card-action"
                  aria-label="Mitglied bearbeiten"
                  @click="navigateToEdit(member)"
                />
                <Button
                  icon="pi pi-trash"
                  size="small"
                  outlined
                  severity="danger"
                  class="member-card-action"
                  aria-label="Mitglied löschen"
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

    <MemberExportDialog
      v-model="showExportDialog"
      :exporting="membersStore.loading"
      @export="handleExportExcel"
    />

    <div v-if="isMobileSearchMode" class="members-search-overlay">
      <div class="members-search-overlay__top">
        <Button
          icon="pi pi-arrow-left"
          text
          rounded
          aria-label="Suche schließen"
          class="members-search-overlay__back"
          @click="closeMobileSearch"
        />

        <IconField class="members-search-overlay__field">
          <InputIcon class="pi pi-search" />
          <InputText
            ref="mobileSearchInputRef"
            v-model="filters.search"
            placeholder="Mitglied suchen..."
            class="w-full"
            @input="onFilterChange"
            @keydown.esc="closeMobileSearch"
          />
        </IconField>
      </div>

      <div class="members-search-overlay__results">
        <div v-if="!filters.search.trim()" class="mobile-search-state">
          <i class="pi pi-search"></i>
          <p>Tippe einen Namen, um Mitglieder zu finden.</p>
        </div>

        <div v-else-if="membersStore.loading" class="mobile-search-state">
          <i class="pi pi-spin pi-spinner"></i>
          <p>Suche läuft...</p>
        </div>

        <div v-else-if="membersStore.members.length" class="mobile-search-results">
          <button
            v-for="member in membersStore.members"
            :key="member.id"
            type="button"
            class="mobile-search-row"
            @click="navigateToView(member)"
          >
            <Avatar
              v-if="member.avatar_url"
              :image="member.avatar_url"
              shape="circle"
              class="mobile-search-row__avatar"
            />
            <Avatar
              v-else
              :label="memberInitials(member)"
              shape="circle"
              class="mobile-search-row__avatar"
            />

            <div class="mobile-search-row__content">
              <span class="mobile-search-row__name">{{ member.full_name }}</span>
              <span class="mobile-search-row__groups">{{ getMemberGroupsLabel(member) }}</span>
            </div>

            <i class="pi pi-chevron-right mobile-search-row__chevron"></i>
          </button>
        </div>

        <div v-else class="mobile-search-state">
          <i class="pi pi-users"></i>
          <p>Keine Treffer gefunden.</p>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useMembersStore } from '@/stores/members'
import { useDepartmentsStore } from '@/stores/departments'
import { membersApi, parentsApi } from '@/api/members'
import type { Member } from '@/types/api'
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
import Avatar from 'primevue/avatar'
import ResponsiveList from '@/components/common/ResponsiveList.vue'
import ParentContacts from '@/components/members/ParentContacts.vue'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import DepartmentBadge from '@/components/departments/atoms/DepartmentBadge.vue'
import MemberExportDialog from '@/components/members/molecules/MemberExportDialog.vue'

const router = useRouter()
const membersStore = useMembersStore()
const departmentsStore = useDepartmentsStore()
const confirm = useConfirm()
const toast = useToast()
const { getInt, getString, syncToUrl } = useQueryTableState()

const showExportDialog = ref(false)
const isMobile = ref(false)
const mobileSearchActive = ref(false)
const mobileSearchInputRef = ref<HTMLInputElement | null>(null)
const originalBodyOverflow = ref<string | null>(null)

const isMobileSearchMode = computed(() => isMobile.value && mobileSearchActive.value)

const updateViewportState = () => {
  isMobile.value = window.innerWidth <= 768
  if (!isMobile.value) {
    mobileSearchActive.value = false
  }
}

onUnmounted(() => {
  window.removeEventListener('resize', updateViewportState)
  if (filterTimeout) {
    clearTimeout(filterTimeout)
  }
  if (originalBodyOverflow.value !== null) {
    document.body.style.overflow = originalBodyOverflow.value
  }
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
interface MemberStats {
  total: number
  gender: { male?: number; female?: number; diverse?: number; unknown?: number }
  age?: { avg?: number | null; min?: number; max?: number; buckets?: { label: string; color?: string; count?: number }[] } | null
  by_status: { name: string; count: number; color: string }[]
  can_swim: number
  by_group: { name: string; count: number }[]
}
const statsExpanded = ref(false)
const statsLoading = ref(false)
const stats = ref<MemberStats | null>(null)

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
  updateViewportState()
  window.addEventListener('resize', updateViewportState)

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

const onPage = (event: { first: number; rows: number }) => {
  lazyParams.first = event.first
  lazyParams.rows = event.rows
  syncToUrl({ search: filters.search, status: filters.status, group: filters.group, gender: filters.gender, offset: lazyParams.first, rows: lazyParams.rows, sortField: lazyParams.sortField, sortOrder: lazyParams.sortOrder }, MEMBERS_URL_DEFAULTS)
  loadLazyData()
}

const onSort = (event: import('primevue/datatable').DataTableSortEvent) => {
  const sf = event.sortField
  lazyParams.sortField = (typeof sf === 'string' ? sf : undefined) || 'lastname'
  lazyParams.sortOrder = (event.sortOrder as 1 | -1) || 1
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

const onSearchFocus = () => {
  if (!isMobile.value) {
    return
  }
  mobileSearchActive.value = true
  nextTick(() => {
    mobileSearchInputRef.value?.focus()
  })
}

const closeMobileSearch = () => {
  mobileSearchActive.value = false
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur()
  }
}

watch(isMobileSearchMode, (enabled) => {
  if (enabled) {
    if (originalBodyOverflow.value === null) {
      originalBodyOverflow.value = document.body.style.overflow
    }
    document.body.style.overflow = 'hidden'
    nextTick(() => {
      mobileSearchInputRef.value?.focus()
    })
    return
  }

  if (originalBodyOverflow.value !== null) {
    document.body.style.overflow = originalBodyOverflow.value
    originalBodyOverflow.value = null
  }
})

const memberInitials = (member: Member) => {
  const first = member.name?.[0] || ''
  const last = member.lastname?.[0] || ''
  const fallback = member.full_name?.[0] || ''
  return `${first}${last}`.trim().toUpperCase() || fallback.toUpperCase()
}

const getMemberGroupsLabel = (member: Member) => {
  const labels: string[] = []

  if (member.group?.name) {
    labels.push(member.group.name)
  }

  if (member.department_ids?.length) {
    const departmentNames = member.department_ids
      .map((deptId) => departmentsStore.departments.find((dept) => dept.id === deptId)?.name)
      .filter((name): name is string => Boolean(name))

    for (const name of departmentNames) {
      if (!labels.includes(name)) {
        labels.push(name)
      }
    }
  }

  return labels.join(' · ') || 'Keine Gruppe'
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
  closeMobileSearch()
  router.push('/members/create')
}

const navigateToView = (member: Member) => {
  closeMobileSearch()
  router.push(`/members/${member.id}`)
}

const navigateToEdit = (member: Member) => {
  closeMobileSearch()
  router.push(`/members/${member.id}/edit`)
}

const onRowClick = (event: { data: Member }) => {
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
      } catch {
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

const handleExportExcel = async (columns: string[]) => {
  try {
    await membersStore.exportExcel(columns)
    showExportDialog.value = false
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Mitgliederliste wurde erfolgreich exportiert',
      life: 3000
    })
  } catch {
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

.filter-search-wrap {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.table-card {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.dept-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
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

.members-search-overlay {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 1200;
  background-color: var(--p-content-background, #ffffff);
  flex-direction: column;
}

.members-search-overlay__top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: calc(env(safe-area-inset-top) + 0.5rem) 0.9rem 0.6rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
}

.members-search-overlay__back {
  flex-shrink: 0;
}

.members-search-overlay__field {
  flex: 1;
}

.members-search-overlay__results {
  flex: 1;
  overflow-y: auto;
  padding: 0.65rem 0.75rem calc(env(safe-area-inset-bottom) + 0.8rem);
  -webkit-overflow-scrolling: touch;
}

.mobile-search-results {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.mobile-search-row {
  width: 100%;
  border: 1px solid var(--surface-border);
  background: var(--surface-card);
  border-radius: calc(var(--border-radius) - 2px);
  display: flex;
  align-items: center;
  gap: 0.55rem;
  text-align: left;
  padding: 0.45rem 0.6rem;
  cursor: pointer;
}

.mobile-search-row__avatar {
  width: 2rem;
  height: 2rem;
  min-width: 2rem;
}

.mobile-search-row__content {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.mobile-search-row__name {
  font-weight: 600;
  line-height: 1.2;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mobile-search-row__groups {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mobile-search-row__chevron {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.mobile-search-state {
  border: 1px dashed var(--surface-border);
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 1.25rem 0.75rem;
  text-align: center;
}

.mobile-search-state p {
  margin: 0;
  font-size: 0.9rem;
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

  .filter-card {
    margin-bottom: 1rem;
  }

  .filter-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.55rem;
  }

  .filter-search-wrap {
    grid-column: 1 / -1;
  }

  .filter-search-wrap--active {
    margin-bottom: 0.25rem;
  }

  .filter-search-field,
  .filter-control {
    width: 100%;
  }

  .filter-search-field {
    flex: 1;
  }

  .filter-search-field :deep(.p-inputtext),
  .filter-control :deep(.p-inputtext),
  .filter-control :deep(.p-dropdown) {
    min-height: 2.35rem;
  }

  .filter-search-field :deep(.p-iconfield .p-inputtext) {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
  }

  .filter-control :deep(.p-dropdown-label) {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
  }

  .member-card {
    border-radius: calc(var(--border-radius) - 2px);
  }

  .member-card .mobile-entity-card__actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .member-card .member-card-action :deep(.p-button-label) {
    display: none;
  }

  .member-card .member-card-action :deep(.p-button-icon) {
    margin-right: 0;
  }

  .member-card .member-card-action :deep(.p-button) {
    justify-content: center;
    min-height: 2.15rem;
    padding: 0.35rem;
  }

  .member-card :deep(.parent-contacts--compact) {
    margin-top: -0.15rem;
  }

  .members-search-overlay {
    display: flex;
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

@media (max-width: 420px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
