<template>
  <div class="qualifications-page">
    <OverviewHeader title="Qualifikationen" subtitle="Gültigkeit, Ablauf und Nachweise im Blick behalten.">
      <template #actions>
        <Button
          icon="pi pi-ellipsis-h"
          :label="isMobile ? undefined : 'Weitere Aktionen'"
          aria-label="Weitere Aktionen"
          severity="secondary"
          outlined
          aria-haspopup="true"
          aria-controls="qualifications-more"
          @click="moreMenu?.toggle($event)"
        />
        <Menu id="qualifications-more" ref="moreMenu" :model="moreItems" popup />
        <Button
          v-if="tab === 'qualifications'"
          label="Neue Qualifikation"
          icon="pi pi-plus"
          @click="router.push('/qualifications/create')"
        />
        <Button v-else label="Neue Sonderaufgabe" icon="pi pi-plus" @click="router.push('/qualifications/specialtasks/create')" />
      </template>
    </OverviewHeader>

    <Tabs :value="tab" class="area-tabs" @update:value="setTab">
      <TabList>
        <Tab value="qualifications">Qualifikationen</Tab>
        <Tab value="tasks">Sonderaufgaben<span v-if="statistics" class="tab-count">{{ statistics.active_special_tasks }}</span></Tab>
      </TabList>
    </Tabs>

    <StateView
      v-if="statisticsError"
      kind="error"
      title="Übersicht konnte nicht geladen werden"
      :message="statisticsError"
      @retry="refreshStatistics"
    />

    <section v-if="tab === 'qualifications'" class="area" aria-label="Qualifikationen">
      <div class="view-controls">
        <SegmentedControl v-model="view" label="Ansicht" :options="viewOptions" />
        <SegmentedControl v-if="view === 'expiring'" v-model="within" label="Zeitraum" :options="windowOptions" />
      </div>
      <p class="view-hint">{{ viewHint }}</p>

      <template v-if="isMobile">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText v-model="mobileSearch" placeholder="Person oder Art suchen" aria-label="Qualifikationen durchsuchen" class="w-full" />
        </IconField>
        <QualificationsMobileList
          :items="mobileQualifications"
          :loading="mobileLoading"
          :rows="mobilePageSize"
          :total-records="mobileTotalRecords"
          @page-change="handleMobilePageChange"
          @view="router.push(`/qualifications/${$event}`)"
        />
      </template>
      <QualificationsTable
        v-else
        ref="tableRef"
        :query="query"
        :page-size="20"
        sort-field="date_expires"
        :sort-order="1"
        @view="router.push(`/qualifications/${$event}`)"
        @edit="router.push(`/qualifications/${$event}/edit`)"
        @delete="handleDeleteQualification"
      />
    </section>

    <section v-else class="area" aria-label="Sonderaufgaben">
      <template v-if="isMobile">
        <div class="mobile-filter-grid">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="mobileSpecialTaskFilters.search" placeholder="Person oder Aufgabe suchen" aria-label="Sonderaufgaben durchsuchen" class="w-full" />
          </IconField>
          <SegmentedControl v-model="mobileSpecialTaskFilters.status" label="Status" :options="taskStatusOptions" />
        </div>
        <SpecialTasksMobileList
          :items="mobileSpecialTasks"
          :loading="mobileSpecialTaskLoading"
          :rows="mobileSpecialTaskPageSize"
          :total-records="mobileSpecialTaskTotalRecords"
          @page-change="handleMobileSpecialTaskPageChange"
          @view="handleViewSpecialTask"
          @edit="handleEditSpecialTask"
          @end="handleEndSpecialTask"
          @delete="handleDeleteSpecialTask"
        />
      </template>
      <template v-else>
        <h2 class="area-title">Aktive Sonderaufgaben</h2>
        <StateView v-if="loadingStatistics && !statistics" kind="loading" />
        <SpecialTasksTable
          v-else-if="activeSpecialTasks.length"
          :tasks="activeSpecialTasks"
          :loading="qualificationsStore.loading"
          @view="handleViewSpecialTask"
          @edit="handleEditSpecialTask"
          @delete="handleDeleteSpecialTask"
          @end="handleEndSpecialTask"
        />
        <StateView v-else-if="statistics" kind="empty" title="Keine aktiven Sonderaufgaben" message="Neue Sonderaufgaben erscheinen hier, bis sie beendet werden." />
      </template>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import type { MenuItem } from 'primevue/menuitem'
import { useQualificationsStore } from '@/stores/qualifications'
import { useMobile } from '@/composables/useMobile'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import SegmentedControl, { type SegmentedOption } from '@/components/common/SegmentedControl.vue'
import StateView from '@/components/common/StateView.vue'
import QualificationsTable from '@/components/qualifications/organisms/QualificationsTable.vue'
import SpecialTasksTable from '@/components/qualifications/organisms/SpecialTasksTable.vue'
import QualificationsMobileList from '@/components/qualifications/organisms/QualificationsMobileList.vue'
import SpecialTasksMobileList from '@/components/qualifications/organisms/SpecialTasksMobileList.vue'
import { EXPIRY_WINDOWS, type ExpiryWindow, type QualificationListParams, type SpecialTaskListParams } from '@/types/qualifications'

type Area = 'qualifications' | 'tasks'
type View = 'expiring' | 'expired' | 'missing' | 'all'

const router = useRouter()
const route = useRoute()
const qualificationsStore = useQualificationsStore()
const toast = useToast()
const confirm = useConfirm()
const { isMobile } = useMobile()
const tableRef = ref<InstanceType<typeof QualificationsTable> | null>(null)
const moreMenu = ref<InstanceType<typeof Menu> | null>(null)

// Area, view and window live in the URL so each list has a stable link.
const tab = computed<Area>(() => (route.query.tab === 'tasks' ? 'tasks' : 'qualifications'))
const view = computed<View>({
  get: () => (['expired', 'missing', 'all'].includes(String(route.query.view)) ? (route.query.view as View) : 'expiring'),
  set: (value) => updateQuery({ view: value === 'expiring' ? undefined : value }),
})
const within = computed<ExpiryWindow>({
  get: () => (EXPIRY_WINDOWS.find((days) => String(days) === route.query.within) ?? 30),
  set: (value) => updateQuery({ within: value === 30 ? undefined : String(value) }),
})

function updateQuery(changes: Record<string, string | undefined>) {
  const next = { ...route.query, ...changes }
  for (const key of Object.keys(next)) if (next[key] === undefined) delete next[key]
  router.replace({ query: next })
}

function setTab(value: string | number) {
  updateQuery({ tab: value === 'tasks' ? 'tasks' : undefined })
}

const statistics = computed(() => qualificationsStore.statistics)
const loadingStatistics = computed(() => qualificationsStore.loadingStatistics)
const statisticsError = ref<string | null>(null)
const activeSpecialTasks = computed(() => statistics.value?.active_special_tasks_list ?? [])

const viewOptions = computed<SegmentedOption<View>[]>(() => {
  const stats = statistics.value
  return [
    { value: 'expiring', label: 'Läuft ab', count: stats?.expiring_by_window?.[`${within.value}`] ?? null },
    { value: 'expired', label: 'Abgelaufen', count: stats?.expired_qualifications ?? null },
    { value: 'missing', label: 'Ohne Nachweis', count: stats?.without_evidence ?? null },
    { value: 'all', label: 'Alle', count: stats?.total_qualifications ?? null },
  ]
})
const windowOptions: SegmentedOption<ExpiryWindow>[] = EXPIRY_WINDOWS.map((days) => ({ value: days, label: `${days} Tage` }))
const taskStatusOptions: SegmentedOption<NonNullable<SpecialTaskListParams['status']>>[] = [
  { value: 'active', label: 'Aktiv' },
  { value: 'ended', label: 'Beendet' },
  { value: 'all', label: 'Alle' },
]

const viewHint = computed(() => ({
  expiring: `Gültige Qualifikationen, die in den nächsten ${within.value} Tagen ablaufen. Verlängerte Einträge zählen nicht doppelt.`,
  expired: 'Abgelaufen und noch nicht verlängert.',
  missing: 'Aktuelle Qualifikationen ohne hinterlegten Nachweis.',
  all: 'Alle Einträge einschließlich früherer, bereits verlängerter Qualifikationen.',
}[view.value]))

const query = computed<Partial<QualificationListParams>>(() => ({
  expiring: { current: true, expiring_within: within.value },
  expired: { current: true, status: 'expired' as const },
  missing: { current: true, without_evidence: true },
  all: {},
}[view.value]))

const moreItems = computed<MenuItem[]>(() => [
  tab.value === 'qualifications'
    ? { label: 'Neue Sonderaufgabe', icon: 'pi pi-plus', command: () => router.push('/qualifications/specialtasks/create') }
    : { label: 'Neue Qualifikation', icon: 'pi pi-plus', command: () => router.push('/qualifications/create') },
  { separator: true },
  { label: 'Qualifikationsarten verwalten', icon: 'pi pi-cog', command: () => router.push('/qualifications/types') },
  { label: 'Aufgabenarten verwalten', icon: 'pi pi-cog', command: () => router.push('/qualifications/specialtasks/types') },
])

// ── Mobile lists ───────────────────────────────────────────────────────────
const mobileSearch = ref('')
const mobilePage = ref(1)
const mobilePageSize = ref(10)
const mobileLoading = ref(false)
const mobileQualifications = computed(() => qualificationsStore.qualifications)
const mobileTotalRecords = computed(() => qualificationsStore.qualificationsTotal)

const mobileSpecialTaskPage = ref(1)
const mobileSpecialTaskPageSize = ref(10)
const mobileSpecialTaskLoading = ref(false)
const mobileSpecialTaskFilters = reactive({
  search: '',
  status: 'active' as NonNullable<SpecialTaskListParams['status']>,
})
const mobileSpecialTasks = computed(() => qualificationsStore.specialTasks)
const mobileSpecialTaskTotalRecords = computed(() => qualificationsStore.specialTasksTotal)
let mobileSearchTimeout: ReturnType<typeof setTimeout> | null = null

async function loadMobileQualifications() {
  if (!isMobile.value || tab.value !== 'qualifications') return
  mobileLoading.value = true
  try {
    await qualificationsStore.fetchQualifications({
      page: mobilePage.value,
      page_size: mobilePageSize.value,
      search: mobileSearch.value || undefined,
      ordering: 'date_expires',
      ...query.value,
    })
  } catch {
    // The store keeps the error; the list shows its empty/error state.
  } finally {
    mobileLoading.value = false
  }
}

async function loadMobileSpecialTasks() {
  if (!isMobile.value || tab.value !== 'tasks') return
  mobileSpecialTaskLoading.value = true
  try {
    await qualificationsStore.fetchSpecialTasks({
      page: mobileSpecialTaskPage.value,
      page_size: mobileSpecialTaskPageSize.value,
      search: mobileSpecialTaskFilters.search || undefined,
      status: mobileSpecialTaskFilters.status !== 'all' ? mobileSpecialTaskFilters.status : undefined,
      ordering: '-start_date',
    })
  } catch {
    // See above.
  } finally {
    mobileSpecialTaskLoading.value = false
  }
}

async function handleMobilePageChange(page: number, size: number) {
  mobilePage.value = page
  mobilePageSize.value = size
  await loadMobileQualifications()
}

async function handleMobileSpecialTaskPageChange(page: number, size: number) {
  mobileSpecialTaskPage.value = page
  mobileSpecialTaskPageSize.value = size
  await loadMobileSpecialTasks()
}

watch([isMobile, tab, query], () => {
  mobilePage.value = 1
  mobileSpecialTaskPage.value = 1
  loadMobileQualifications()
  loadMobileSpecialTasks()
})
watch(() => mobileSpecialTaskFilters.status, () => {
  mobileSpecialTaskPage.value = 1
  loadMobileSpecialTasks()
})
watch([mobileSearch, () => mobileSpecialTaskFilters.search], () => {
  if (mobileSearchTimeout) clearTimeout(mobileSearchTimeout)
  mobileSearchTimeout = setTimeout(() => {
    mobilePage.value = 1
    mobileSpecialTaskPage.value = 1
    loadMobileQualifications()
    loadMobileSpecialTasks()
  }, 350)
})

async function refreshStatistics() {
  statisticsError.value = null
  try {
    await qualificationsStore.fetchStatistics()
  } catch {
    statisticsError.value = 'Zähler und aktive Sonderaufgaben fehlen. Die Listen selbst bleiben nutzbar.'
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
        await tableRef.value?.reload(true)
        if (isMobile.value) await loadMobileQualifications()
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
    acceptClass: 'p-button-warn',
    accept: async () => {
      try {
        await qualificationsStore.endSpecialTask(id)
        await refreshStatistics()
        if (isMobile.value) await loadMobileSpecialTasks()
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
        if (isMobile.value) await loadMobileSpecialTasks()
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

onMounted(async () => {
  await Promise.all([refreshStatistics(), loadMobileQualifications(), loadMobileSpecialTasks()])
})

onUnmounted(() => {
  if (mobileSearchTimeout) clearTimeout(mobileSearchTimeout)
})
</script>

<style scoped>
.qualifications-page {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}
.qualifications-page :deep(.overview-header) { margin-bottom: 0; }

.area-tabs :deep(:is(.p-tablist, .p-tablist-content, .p-tablist-tab-list)) { background: transparent; }
.tab-count {
  margin-left: var(--jf-space-1);
  padding: 0 6px;
  border-radius: 999px;
  background: var(--jf-color-ground);
  font-size: var(--jf-text-xs);
}

.area { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.area-title { margin: 0; font-size: var(--jf-text-lg); }
.view-controls { display: flex; flex-wrap: wrap; gap: var(--jf-space-1-5); }
.view-hint { margin: calc(-1 * var(--jf-space-1)) 0 0; font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); }
.mobile-filter-grid { display: flex; flex-direction: column; gap: var(--jf-space-1-5); }
</style>
