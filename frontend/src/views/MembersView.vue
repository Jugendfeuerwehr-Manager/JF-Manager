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
          severity="success"
          outlined
          :loading="membersStore.loading"
          @click="showExportDialog = true"
        />
        <Button
          label="Mitglied hinzufügen"
          icon="pi pi-plus"
          severity="primary"
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
import { onMounted, ref } from 'vue'
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
import OverviewHeader from '@/components/layout/OverviewHeader.vue'
import MembersFilters from '@/components/members/molecules/MembersFilters.vue'
import MembersStatsPanel from '@/components/members/molecules/MembersStatsPanel.vue'
import MembersSearchOverlay from '@/components/members/molecules/MembersSearchOverlay.vue'
import MembersList from '@/components/members/organisms/MembersList.vue'
import MemberExportDialog from '@/components/members/molecules/MemberExportDialog.vue'
import MemberDeletionDialog from '@/components/members/molecules/MemberDeletionDialog.vue'

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
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler', detail: 'Mitglied konnte nicht gelöscht werden', life: 3000 })
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
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .members-view {
    padding: 1rem;
  }
}
</style>


