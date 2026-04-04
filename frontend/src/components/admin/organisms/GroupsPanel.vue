<template>
  <div class="groups-panel" :class="{ 'mobile': isMobile }">
    <!-- Master list -->
    <div
      class="master-pane"
      :class="{ 'hidden-mobile': isMobile && selectedGroupId !== null }"
    >
      <Toolbar class="mb-3">
        <template #start>
          <InputText
            v-model="search"
            placeholder="Suchen..."
            size="small"
            class="mr-2"
            @input="handleSearch"
          />
        </template>
        <template #end>
          <Button
            icon="pi pi-plus"
            label="Neu"
            size="small"
            @click="openNew"
          />
        </template>
      </Toolbar>

      <div v-if="adminStore.groupsLoading" class="flex justify-content-center py-6">
        <ProgressSpinner style="width: 32px; height: 32px" stroke-width="4" />
      </div>

      <div v-else class="group-list">
        <div
          v-for="group in adminStore.groups"
          :key="group.id"
          class="group-list-item"
          :class="{ 'active': selectedGroupId === group.id }"
          @click="selectGroup(group.id)"
        >
          <div class="flex align-items-center gap-2">
            <div class="group-initial" :style="{ background: groupColor(group.id) }">
              {{ group.name.charAt(0).toUpperCase() }}
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium text-sm truncate">{{ group.name }}</div>
              <div class="text-xs text-color-secondary">
                {{ group.user_count }} Benutzer · {{ group.permissions_count }} Berechtigungen
              </div>
            </div>
          </div>
        </div>

        <div v-if="adminStore.groups.length === 0" class="master-empty">
          <div class="master-empty-icon"><i class="pi pi-users" /></div>
          <div class="master-empty-text">Noch keine Gruppen</div>
          <div class="master-empty-sub">Erstelle eine Gruppe mit dem + Button</div>
        </div>
      </div>
    </div>

    <!-- Detail pane -->
    <div
      class="detail-pane"
      :class="{ 'hidden-mobile': isMobile && selectedGroupId === null && !showNew }"
    >
      <!-- Mobile back button -->
      <Button
        v-if="isMobile"
        icon="pi pi-arrow-left"
        label="Zurück"
        text
        size="small"
        class="mb-3"
        @click="closeDetail"
      />

      <div v-if="detailLoading" class="flex justify-content-center py-6">
        <ProgressSpinner style="width: 32px; height: 32px" stroke-width="4" />
      </div>

      <GroupDetailForm
        v-else-if="showForm"
        :group="selectedGroupDetail"
        @saved="handleSaved"
        @cancel="handleCancel"
      />

      <div v-else class="detail-empty">
        <div class="detail-empty-illustration">
          <div class="detail-empty-circle">
            <i class="pi pi-users" />
          </div>
        </div>
        <h3 class="detail-empty-title">Keine Gruppe ausgewählt</h3>
        <p class="detail-empty-sub">Wähle eine Gruppe aus der Liste oder erstelle eine neue.</p>
        <Button
          label="Neue Gruppe erstellen"
          icon="pi pi-plus"
          size="small"
          @click="openNew"
        />
      </div>

      <!-- Delete button in detail footer (only for existing groups) -->
      <div
        v-if="selectedGroupId !== null && !showNew && !detailLoading && selectedGroupDetail"
        class="detail-footer flex justify-content-end mt-4 pt-3 border-top-1 border-200"
      >
        <Button
          icon="pi pi-trash"
          label="Gruppe löschen"
          severity="danger"
          text
          size="small"
          @click="confirmDelete"
        />
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Toolbar from 'primevue/toolbar'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import GroupDetailForm from '@/components/admin/molecules/GroupDetailForm.vue'
import type { AuthGroupDetail } from '@/types/admin'

const adminStore = useAdminStore()
const confirm = useConfirm()
const toast = useToast()

function groupColor(id: number): string {
  const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#ef4444', '#14b8a6']
  return colors[id % colors.length] ?? '#6366f1'
}

const search = ref('')
const selectedGroupId = ref<number | null>(null)
const selectedGroupDetail = ref<AuthGroupDetail | null>(null)
const detailLoading = ref(false)
const showNew = ref(false)

const isMobile = ref(window.innerWidth < 768)

window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
})

const showForm = computed(() => showNew.value || selectedGroupId.value !== null)

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function handleSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    adminStore.fetchGroups({ search: search.value, limit: 200 })
  }, 300)
}

async function selectGroup(id: number) {
  selectedGroupId.value = id
  showNew.value = false
  detailLoading.value = true
  selectedGroupDetail.value = null
  try {
    selectedGroupDetail.value = await adminStore.fetchGroup(id)
  } finally {
    detailLoading.value = false
  }
}

function openNew() {
  selectedGroupId.value = null
  selectedGroupDetail.value = null
  showNew.value = true
}

function closeDetail() {
  selectedGroupId.value = null
  showNew.value = false
  selectedGroupDetail.value = null
}

async function handleSaved(groupId: number) {
  showNew.value = false
  await adminStore.fetchGroups({ limit: 200 })
  await selectGroup(groupId)
}

function handleCancel() {
  if (showNew.value) {
    showNew.value = false
  }
}

function confirmDelete() {
  confirm.require({
    message: `Gruppe "${selectedGroupDetail.value?.name}" wirklich löschen?`,
    header: 'Gruppe löschen',
    icon: 'pi pi-trash',
    rejectLabel: 'Abbrechen',
    acceptLabel: 'Löschen',
    acceptSeverity: 'danger',
    accept: async () => {
      try {
        await adminStore.deleteGroup(selectedGroupId.value!)
        toast.add({ severity: 'success', summary: 'Gelöscht', life: 3000 })
        closeDetail()
        await adminStore.fetchGroups({ limit: 200 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler beim Löschen', life: 4000 })
      }
    },
  })
}

onMounted(async () => {
  await adminStore.fetchGroups({ limit: 200 })
})
</script>

<style scoped>
.groups-panel {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1rem;
  height: 100%;
  min-height: 600px;
}

.groups-panel.mobile {
  grid-template-columns: 1fr;
}

.master-pane {
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.master-pane .p-toolbar {
  border-radius: 0;
  border: none;
  border-bottom: 1px solid var(--p-content-border-color);
}

.group-list {
  overflow-y: auto;
  flex: 1;
  padding: 0.25rem;
}

.group-list-item {
  padding: 0.625rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.group-list-item:hover {
  background: var(--p-content-hover-background);
}

.group-list-item.active {
  background: var(--p-primary-50, #eff6ff);
  border-left: 3px solid var(--p-primary-color);
}

.group-initial {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 0.875rem;
}

.detail-pane {
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
  padding: 1.25rem;
  overflow-y: auto;
}

.master-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.master-empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--p-content-hover-background);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin-bottom: 0.75rem;
}

.master-empty-text {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.master-empty-sub {
  font-size: 0.8rem;
  opacity: 0.7;
}

.detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  text-align: center;
  padding: 2rem;
}

.detail-empty-illustration {
  margin-bottom: 1.5rem;
}

.detail-empty-circle {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--p-primary-100, #dbeafe), var(--p-primary-200, #bfdbfe));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  color: var(--p-primary-500, #3b82f6);
  margin: 0 auto;
}

.detail-empty-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0 0 0.5rem;
}

.detail-empty-sub {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  margin: 0 0 1.5rem;
  max-width: 260px;
}

.hidden-mobile {
  display: none;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
