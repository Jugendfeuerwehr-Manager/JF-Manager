<template>
  <div class="locations-management">
    <!-- Header -->
    <div class="section-header">
      <h3>
        <i class="pi pi-map-marker"></i>
        Lagerorte verwalten
      </h3>
      <Button label="Neuer Lagerort" icon="pi pi-plus" @click="openCreateDialog" />
    </div>

    <!-- Filters -->
    <Card class="filter-card">
      <template #content>
        <div class="filter-grid">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText v-model="filters.search" placeholder="Lagerort suchen..." />
          </IconField>

          <Dropdown
            v-model="filters.type"
            :options="typeOptions"
            option-label="label"
            option-value="value"
            placeholder="Typ"
            show-clear
          />
        </div>
      </template>
    </Card>

    <!-- Tabs for Storage vs Members -->
    <TabView>
      <TabPanel :value="0" header="Lagerorte">
        <div class="locations-grid">
          <Card
            v-for="location in filteredStorageLocations"
            :key="location.id"
            class="location-card"
            @click="openEditDialog(location)"
          >
            <template #content>
              <div class="location-content">
                <div class="location-info">
                  <div class="location-header">
                    <i class="pi pi-box location-icon"></i>
                    <span class="location-name">{{ location.name }}</span>
                  </div>
                  <span v-if="location.parent_name" class="location-path">
                    {{ location.full_path }}
                  </span>
                </div>
                <div class="location-stats">
                  <Tag :value="`${getLocationStockCount(location.id)} Artikel`" severity="secondary" />
                </div>
                <div class="location-actions">
                  <Button
                    icon="pi pi-pencil"
                    size="small"
                    text
                    rounded
                    @click.stop="openEditDialog(location)"
                  />
                  <Button
                    icon="pi pi-trash"
                    size="small"
                    text
                    rounded
                    severity="danger"
                    @click.stop="confirmDelete(location)"
                  />
                </div>
              </div>
            </template>
          </Card>

          <Card v-if="filteredStorageLocations.length === 0" class="empty-card">
            <template #content>
              <div class="empty-content">
                <i class="pi pi-inbox"></i>
                <p>Keine Lagerorte gefunden</p>
                <Button label="Lagerort erstellen" icon="pi pi-plus" @click="openCreateDialog" />
              </div>
            </template>
          </Card>
        </div>
      </TabPanel>

      <TabPanel :value="1" header="Mitglieder-Lagerorte">
        <div class="locations-grid">
          <Card
            v-for="location in filteredMemberLocations"
            :key="location.id"
            class="location-card member-location"
            @click="openEditDialog(location)"
          >
            <template #content>
              <div class="location-content">
                <div class="location-info">
                  <div class="location-header">
                    <i class="pi pi-user location-icon"></i>
                    <span class="location-name">{{ location.name }}</span>
                  </div>
                  <LocationTypeBadge :is-member="true" />
                </div>
                <div class="location-stats">
                  <Tag :value="`${getLocationStockCount(location.id)} ausgeliehen`" severity="info" />
                </div>
                <div class="location-actions">
                  <Button
                    icon="pi pi-eye"
                    size="small"
                    text
                    rounded
                    title="Ausleihen anzeigen"
                    @click.stop="viewMemberLoans(location)"
                  />
                  <Button
                    icon="pi pi-trash"
                    size="small"
                    text
                    rounded
                    severity="danger"
                    @click.stop="confirmDelete(location)"
                  />
                </div>
              </div>
            </template>
          </Card>

          <Card v-if="filteredMemberLocations.length === 0" class="empty-card">
            <template #content>
              <div class="empty-content">
                <i class="pi pi-users"></i>
                <p>Keine Mitglieder-Lagerorte gefunden</p>
                <p class="text-muted">
                  Mitglieder-Lagerorte werden automatisch erstellt, wenn ein Mitglied Artikel ausleiht.
                </p>
                <Button label="Manuell erstellen" icon="pi pi-plus" @click="openCreateMemberDialog" />
              </div>
            </template>
          </Card>
        </div>
      </TabPanel>
    </TabView>

    <!-- Location Form Dialog -->
    <LocationFormDialog
      v-model="showLocationDialog"
      :location="selectedLocation"
      @success="onLocationSaved"
    />

    <!-- Delete Confirmation -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Dropdown from 'primevue/dropdown'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Tag from 'primevue/tag'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { useRouter } from 'vue-router'
import LocationTypeBadge from '../atoms/LocationTypeBadge.vue'
import LocationFormDialog from '../molecules/LocationFormDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { StorageLocation } from '@/types/inventory'

const inventoryStore = useInventoryStore()
const confirm = useConfirm()
const toast = useToast()
const router = useRouter()

const filters = ref({
  search: '',
  type: null as string | null
})

const showLocationDialog = ref(false)
const selectedLocation = ref<StorageLocation | null>(null)
const createAsMember = ref(false)

const typeOptions = [
  { label: 'Alle', value: null },
  { label: 'Nur Lagerorte', value: 'storage' },
  { label: 'Nur Mitglieder', value: 'member' }
]

const filteredStorageLocations = computed(() => {
  return inventoryStore.storageLocations.filter((loc) => {
    if (filters.value.search) {
      const searchLower = filters.value.search.toLowerCase()
      if (!loc.name.toLowerCase().includes(searchLower) &&
          !(loc.full_path || '').toLowerCase().includes(searchLower)) {
        return false
      }
    }
    return true
  })
})

const filteredMemberLocations = computed(() => {
  return inventoryStore.memberLocations.filter((loc) => {
    if (filters.value.search) {
      const searchLower = filters.value.search.toLowerCase()
      if (!loc.name.toLowerCase().includes(searchLower)) {
        return false
      }
    }
    return true
  })
})

function getLocationStockCount(locationId: number): number {
  return inventoryStore.stocks
    .filter((s) => s.location === locationId)
    .reduce((sum, s) => sum + s.quantity, 0)
}

function openCreateDialog() {
  selectedLocation.value = null
  createAsMember.value = false
  showLocationDialog.value = true
}

function openCreateMemberDialog() {
  selectedLocation.value = null
  createAsMember.value = true
  showLocationDialog.value = true
}

function openEditDialog(location: StorageLocation) {
  selectedLocation.value = location
  showLocationDialog.value = true
}

function viewMemberLoans(location: StorageLocation) {
  // Navigate to loans tab with filter
  router.push({ name: 'inventory-loans', query: { member: location.member } })
}

function confirmDelete(location: StorageLocation) {
  const stockCount = getLocationStockCount(location.id)

  if (stockCount > 0) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: `Der Lagerort "${location.name}" enthält noch ${stockCount} Artikel und kann nicht gelöscht werden.`,
      life: 5000
    })
    return
  }

  confirm.require({
    message: `Möchten Sie den Lagerort "${location.name}" wirklich löschen?`,
    header: 'Lagerort löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await inventoryStore.deleteLocation(location.id)
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: 'Lagerort wurde gelöscht',
          life: 3000
        })
      } catch {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: 'Lagerort konnte nicht gelöscht werden',
          life: 5000
        })
      }
    }
  })
}

function onLocationSaved() {
  showLocationDialog.value = false
  selectedLocation.value = null
}
</script>

<style scoped>
.locations-management {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-card {
  background: var(--surface-card);
}

.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.locations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.location-card {
  cursor: pointer;
  transition: all 0.2s ease;
}

.location-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.member-location {
  border-left: 4px solid var(--primary-color);
}

.location-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.location-info {
  flex: 1;
  min-width: 0;
}

.location-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.location-icon {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.location-name {
  font-weight: 600;
  font-size: 1rem;
}

.location-path {
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

.location-stats {
  padding: 0 1rem;
}

.location-actions {
  display: flex;
  gap: 0.25rem;
}

.empty-card {
  grid-column: 1 / -1;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  text-align: center;
}

.empty-content i {
  font-size: 3rem;
  color: var(--text-color-secondary);
  margin-bottom: 1rem;
}

.empty-content p {
  margin: 0 0 0.5rem;
}

.text-muted {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .locations-grid {
    grid-template-columns: 1fr;
  }
}
</style>
