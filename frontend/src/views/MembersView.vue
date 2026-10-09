<template>
  <div class="members-view">
    <OverviewHeader
      title="Mitglieder"
      :subtitle="subtitle"
    >
      <template #actions>
        <Button
          v-if="canExport(exportAuth.user, 'export_member', departmentsStore.activeDepartmentId)"
          label="Exportieren"
          icon="pi pi-download"
          severity="secondary"
          outlined
          :loading="membersStore.loading"
          @click="showExportDialog = true"
        />
        <Button
          v-if="!isMobile"
          label="Mitglied anlegen"
          icon="pi pi-plus"
          @click="router.push('/members/create')"
        />
      </template>
    </OverviewHeader>

    <MembersFilters
      :filters="filters"
      :statuses="membersStore.statuses || []"
      :groups="membersStore.groups || []"
      :mobile-search-mode="isMobileSearchMode"
      @update:filters="Object.assign(filters, $event)"
      @filter-change="onFilterChange"
      @search-focus="onSearchFocus"
      @search-esc="closeMobileSearch"
    />

    <MembersStatsPanel
      :stats="stats"
      :loading="statsLoading"
      :expanded="statsExpanded"
      :total-members="membersStore.pagination.count"
      @toggle="toggleStats"
    />

    <MembersList
      v-if="!isMobileSearchMode"
      :members="membersStore.members"
      :loading="membersStore.loading"
      :first="lazyParams.first"
      :rows="lazyParams.rows"
      :total-records="membersStore.pagination.count"
      :departments="departmentsStore.departments"
      :show-departments="departmentsStore.isAllDepartments && departmentsStore.departments.length > 1"
      @page="onPage"
      @sort="onSort"
      @view="(m) => router.push(`/members/${m.id}`)"
      @edit="(m) => router.push(`/members/${m.id}/edit`)"
      @delete="confirmDelete"
    />

    <MembersSearchOverlay
      v-if="isMobileSearchMode"
      :search="filters.search"
      :members="membersStore.members"
      :loading="membersStore.loading"
      :departments="departmentsStore.departments"
      @close="closeMobileSearch"
      @select="(m) => { closeMobileSearch(); router.push(`/members/${m.id}`) }"
      @update:search="filters.search = $event"
      @search-change="onFilterChange"
    />

    <router-link v-if="isMobile && !isMobileSearchMode" to="/members/create" class="create-fab">
      <i class="pi pi-plus" aria-hidden="true"></i>Anlegen
    </router-link>

    <MemberExportDialog
      v-model="showExportDialog"
      :exporting="membersStore.loading"
      @export="handleExportExcel"
    />

    <MemberDeletionDialog
      v-model="showDeletionDialog"
      :member-name="deletionConflict.memberName"
      :transaction-count="deletionConflict.transactionCount"
      :loading="deletionLoading"
      @confirm="handleDeletionStrategy"
      @cancel="showDeletionDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { canExport } from '@/utils/exportPermission'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import { useMembersStore } from '@/stores/members'
import { useDepartmentsStore } from '@/stores/departments'
import { membersApi, parentsApi } from '@/api/members'
import type { Member } from '@/types/members'
import type { Parent } from '@/types/parents'
import type { MemberDeletionStrategy } from '@/types/inventory'
import { useMembersTableState } from '@/composables/useMembersTableState'
import { useMembersMobileSearch } from '@/composables/useMembersMobileSearch'
import { useMembersStats } from '@/composables/useMembersStats'
import { useMobile } from '@/composables/useMobile'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import MembersFilters from '@/components/members/molecules/MembersFilters.vue'
import MembersStatsPanel from '@/components/members/molecules/MembersStatsPanel.vue'
import MembersSearchOverlay from '@/components/members/molecules/MembersSearchOverlay.vue'
import MembersList from '@/components/members/organisms/MembersList.vue'
import MemberExportDialog from '@/components/members/molecules/MemberExportDialog.vue'
import MemberDeletionDialog from '@/components/members/molecules/MemberDeletionDialog.vue'

const exportAuth = useAuthStore()
const router = useRouter()
const membersStore = useMembersStore()
const departmentsStore = useDepartmentsStore()
const confirm = useConfirm()
const toast = useToast()

const showExportDialog = ref(false)
const showDeletionDialog = ref(false)
const deletionLoading = ref(false)
const deletionConflict = ref({ memberName: '', transactionCount: 0 })
let pendingDeleteMember: Member | null = null

const { filters, lazyParams, loadData, onPage, onSort, onFilterChange } = useMembersTableState()
const { isMobileSearchMode, onSearchFocus, closeMobileSearch } = useMembersMobileSearch()
const { stats, statsLoading, statsExpanded, toggleStats } = useMembersStats()
const { isMobile } = useMobile()

const subtitle = computed(() => {
  const count = membersStore.pagination.count
  const department = departmentsStore.activeDepartment
  const scope = department ? ` in ${department.code}` : ''
  return membersStore.loading && !count ? 'Mitglieder werden geladen …' : `${count} ${count === 1 ? 'Mitglied' : 'Mitglieder'}${scope}`
})

onMounted(async () => {
  await Promise.all([membersStore.fetchStatuses(), membersStore.fetchGroups()])
  loadData()
})

const confirmDelete = (member: Member) => {
  const orphanedParents = (member.parents || []).filter(
    (p) => p.children.length === 1 && p.children[0] === member.id,
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
        toast.add({ severity: 'success', summary: 'Erfolg', detail: 'Mitglied wurde gelöscht', life: 3000 })
        loadData()

        if (orphanedParents.length > 0) {
          promptOrphanedParentsDeletion(orphanedParents)
        }
      } catch (err: unknown) {
        const axiosErr = err as { response?: { status?: number; data?: { transaction_count?: number; member_name?: string } } }
        if (axiosErr.response?.status === 409 && axiosErr.response.data?.transaction_count !== undefined) {
          deletionConflict.value = {
            memberName: axiosErr.response.data.member_name ?? member.full_name,
            transactionCount: axiosErr.response.data.transaction_count,
          }
          pendingDeleteMember = member
          showDeletionDialog.value = true
        } else {
          toast.add({ severity: 'error', summary: 'Fehler', detail: 'Mitglied konnte nicht gelöscht werden', life: 3000 })
        }
      }
    },
  })
}

async function handleDeletionStrategy(strategy: MemberDeletionStrategy) {
  if (!pendingDeleteMember) return
  const member = pendingDeleteMember
  deletionLoading.value = true
  try {
    await membersApi.deleteWithStrategy(member.id, strategy)
    membersStore.members = membersStore.members.filter((m) => m.id !== member.id)
    showDeletionDialog.value = false
    pendingDeleteMember = null
    toast.add({ severity: 'success', summary: 'Erfolg', detail: 'Mitglied wurde gelöscht', life: 3000 })
    loadData()
  } catch (error) {
    const response = error as { response?: { data?: { detail?: string } } }
    toast.add({ severity: 'error', summary: 'Fehler', detail: response.response?.data?.detail ?? 'Mitglied konnte nicht gelöscht werden', life: 5000 })
  } finally {
    deletionLoading.value = false
  }
}

function promptOrphanedParentsDeletion(orphanedParents: Parent[]) {
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
        toast.add({ severity: 'success', summary: 'Eltern gelöscht', detail: `${orphanedParents.length === 1 ? 'Elternteil wurde' : 'Elternteile wurden'} gelöscht`, life: 3000 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler', detail: 'Elternteile konnten nicht gelöscht werden', life: 3000 })
      }
    },
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
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 1400px;
  margin: 0 auto;
  padding-bottom: var(--jf-space-6);
}

.members-view :deep(.overview-header) {
  margin-bottom: 0;
}

.create-fab {
  position: fixed;
  right: var(--jf-space-2);
  bottom: calc(80px + env(safe-area-inset-bottom, 0px));
  z-index: 950;
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: 56px;
  padding: 0 var(--jf-space-3);
  border-radius: 16px;
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
  box-shadow: var(--jf-shadow-lg);
}

@media (max-width: 480px) {
  /* gap between header, filters, stats and list: 1rem -> 0.5rem */
  .members-view {
    gap: var(--jf-space-1);
  }

  /* header: padding-bottom 1.5rem -> 0.25rem, gaps 1.5rem -> 0.5rem */
  .members-view :deep(.overview-header) {
    gap: var(--jf-space-1);
    padding: 0;
  }

  .members-view :deep(.overview-header__subtitle) {
    font-size: var(--jf-text-sm);
  }
}
</style>

