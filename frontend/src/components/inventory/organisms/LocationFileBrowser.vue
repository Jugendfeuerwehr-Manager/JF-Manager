<template>
  <div class="location-file-browser">
    <!-- Header -->
    <div class="browser-header">
      <h3>
        <i class="pi pi-folder-open"></i>
        Lagerorte
      </h3>
      <div class="header-actions">
        <Button 
          icon="pi pi-plus" 
          label="Neuer Lagerort" 
          size="small"
          @click="openCreateLocationDialog(null)" 
        />
      </div>
    </div>

    <!-- Main Content: Sidebar + Detail -->
    <div class="browser-content">
      <!-- Sidebar: Location Tree -->
      <div class="browser-sidebar">
        <!-- Tabs for Storage vs Members -->
        <div class="sidebar-tabs">
          <Button
            :label="`Lager (${storageLocations.length})`"
            :outlined="activeTab !== 'storage'"
            size="small"
            @click="activeTab = 'storage'"
          />
          <Button
            :label="`Mitglieder (${memberLocations.length})`"
            :outlined="activeTab !== 'members'"
            size="small"
            @click="activeTab = 'members'"
          />
        </div>

        <!-- Search -->
        <div class="sidebar-search">
          <IconField>
            <InputIcon class="pi pi-search" />
            <InputText 
              v-model="searchQuery" 
              placeholder="Suchen..." 
              class="w-full"
            />
          </IconField>
        </div>

        <!-- Storage Locations Tree -->
        <div v-if="activeTab === 'storage'" class="sidebar-tree">
          <Tree
            v-model:selectionKeys="selectedTreeKey"
            :value="storageLocationTree"
            selectionMode="single"
            class="location-tree"
            @node-select="onNodeSelect"
          >
            <template #default="{ node }">
              <div 
                class="tree-node"
                :class="{ 'drop-target': dropTarget === node.key }"
                @dragover.prevent="onDragOver($event, node)"
                @dragleave="onDragLeave"
                @drop="onDropOnLocation($event, node)"
              >
                <i :class="node.data?.is_member ? 'pi pi-user' : 'pi pi-folder'"></i>
                <span class="node-label">{{ node.label }}</span>
                <Tag 
                  v-if="node.data?.stockCount" 
                  :value="node.data.stockCount" 
                  severity="secondary" 
                  size="small" 
                />
              </div>
            </template>
          </Tree>

          <!-- Add root location button -->
          <div class="add-root-location">
            <Button
              icon="pi pi-plus"
              label="Hauptlagerort hinzufügen"
              text
              size="small"
              class="w-full"
              @click="openCreateLocationDialog(null)"
            />
          </div>
        </div>

        <!-- Member Locations List -->
        <div v-else class="sidebar-members">
          <div
            v-for="location in filteredMemberLocations"
            :key="location.id"
            class="member-item"
            :class="{ selected: selectedLocation?.id === location.id }"
            @click="selectLocation(location)"
            @dragover.prevent="onDragOver($event, { key: String(location.id), data: location })"
            @dragleave="onDragLeave"
            @drop="onDropOnLocation($event, { key: String(location.id), data: location })"
          >
            <i class="pi pi-user"></i>
            <span class="member-name">{{ location.name }}</span>
            <Tag 
              :value="getLocationStockCount(location.id)" 
              severity="info" 
              size="small" 
            />
          </div>
          <div v-if="filteredMemberLocations.length === 0" class="empty-members">
            <small>Keine Mitglieder gefunden</small>
          </div>
        </div>
      </div>

      <!-- Detail Panel -->
      <div class="browser-detail">
        <template v-if="selectedLocation">
          <!-- Location Header -->
          <div class="detail-header">
            <div class="location-info">
              <div class="location-title">
                <i :class="selectedLocation.is_member ? 'pi pi-user' : 'pi pi-folder'"></i>
                <h4>{{ selectedLocation.name }}</h4>
              </div>
              <span v-if="selectedLocation.full_path" class="location-path">
                {{ selectedLocation.full_path }}
              </span>
            </div>
            <div class="location-actions">
              <Button
                v-if="!selectedLocation.is_member"
                icon="pi pi-plus"
                label="Unterordner"
                size="small"
                outlined
                @click="openCreateLocationDialog(selectedLocation.id)"
              />
              <Button
                icon="pi pi-pencil"
                size="small"
                text
                rounded
                title="Bearbeiten"
                @click="openEditLocationDialog(selectedLocation)"
              />
              <Button
                icon="pi pi-trash"
                size="small"
                text
                rounded
                severity="danger"
                title="Löschen"
                @click="confirmDeleteLocation(selectedLocation)"
              />
            </div>
          </div>

          <!-- Stock Items at this Location -->
          <div class="detail-content">
            <div class="content-header">
              <span class="content-title">
                Artikel ({{ locationStocks.length }})
              </span>
              <Button
                v-if="!selectedLocation.is_member"
                icon="pi pi-plus"
                label="Einlagern"
                size="small"
                @click="openAddStockDialog"
              />
            </div>

            <DataTable
              v-if="locationStocks.length > 0"
              :value="locationStocks"
              :paginator="locationStocks.length > 10"
              :rows="10"
              class="stock-table"
              responsiveLayout="scroll"
            >
              <Column header="Artikel" field="display_name" sortable>
                <template #body="{ data }">
                  <div 
                    class="article-cell"
                    draggable="true"
                    @dragstart="onDragStart($event, data)"
                    @dragend="onDragEnd"
                  >
                    <i class="pi pi-bars drag-handle"></i>
                    <span>{{ data.display_name }}</span>
                    <Tag 
                      v-if="data.category_name" 
                      :value="data.category_name" 
                      severity="secondary" 
                      size="small" 
                    />
                  </div>
                </template>
              </Column>
              <Column header="Menge" field="quantity" style="width: 100px" sortable>
                <template #body="{ data }">
                  <Tag :value="data.quantity" :severity="data.quantity > 0 ? 'success' : 'danger'" />
                </template>
              </Column>
              <Column header="Aktionen" style="width: 150px">
                <template #body="{ data }">
                  <div class="action-buttons">
                    <Button
                      v-if="selectedLocation.is_member"
                      icon="pi pi-undo"
                      size="small"
                      text
                      rounded
                      title="Zurückgeben"
                      @click="openReturnDialog(data)"
                    />
                    <Button
                      v-else
                      icon="pi pi-user"
                      size="small"
                      text
                      rounded
                      title="Ausleihen"
                      @click="openLoanDialog(data)"
                    />
                    <Button
                      icon="pi pi-arrow-right"
                      size="small"
                      text
                      rounded
                      title="Verschieben"
                      @click="openMoveDialog(data)"
                    />
                  </div>
                </template>
              </Column>
            </DataTable>

            <div v-else class="empty-stock">
              <i class="pi pi-inbox"></i>
              <p>Keine Artikel an diesem Ort</p>
              <Button
                v-if="!selectedLocation.is_member"
                icon="pi pi-plus"
                label="Artikel einlagern"
                @click="openAddStockDialog"
              />
            </div>
          </div>
        </template>

        <!-- No Selection -->
        <div v-else class="no-selection">
          <i class="pi pi-folder-open"></i>
          <p>Wähle einen Lagerort aus der Liste</p>
        </div>
      </div>
    </div>

    <!-- Dialogs -->
    <LocationFormDialog
      v-model="showLocationDialog"
      :location="editingLocation"
      :default-parent="defaultParentId"
      @success="onLocationSaved"
    />

    <TransactionDialog
      v-model="showTransactionDialog"
      :initial-type="transactionType"
      :initial-stock="selectedStock"
      @success="onTransactionComplete"
    />

    <ConfirmDialog group="location" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Tree from 'primevue/tree'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import LocationFormDialog from '../molecules/LocationFormDialog.vue'
import TransactionDialog from '../molecules/TransactionDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { StorageLocation, Stock, TransactionType } from '@/types/inventory'
import type { TreeNode as PrimeTreeNode } from 'primevue/treenode'

interface TreeNodeData extends StorageLocation {
  stockCount: number
}

interface TreeNode extends PrimeTreeNode {
  key: string
  label: string
  data: TreeNodeData
  children?: TreeNode[]
}

const inventoryStore = useInventoryStore()
const confirm = useConfirm()
const toast = useToast()

// State
const activeTab = ref<'storage' | 'members'>('storage')
const searchQuery = ref('')
const selectedTreeKey = ref<Record<string, boolean>>({})
const selectedLocation = ref<StorageLocation | null>(null)
const showLocationDialog = ref(false)
const editingLocation = ref<StorageLocation | null>(null)
const defaultParentId = ref<number | null>(null)
const showTransactionDialog = ref(false)
const transactionType = ref<TransactionType>('IN')
const selectedStock = ref<Stock | undefined>(undefined)

// Drag and drop state
const draggedStock = ref<Stock | null>(null)
const dropTarget = ref<string | null>(null)

// Computed
const storageLocations = computed(() => inventoryStore.storageLocations)
const memberLocations = computed(() => inventoryStore.memberLocations)

const filteredMemberLocations = computed(() => {
  if (!searchQuery.value) return memberLocations.value
  const query = searchQuery.value.toLowerCase()
  return memberLocations.value.filter(loc => 
    loc.name.toLowerCase().includes(query)
  )
})

// Build tree structure for storage locations
const storageLocationTree = computed((): TreeNode[] => {
  const locations = storageLocations.value
  const query = searchQuery.value.toLowerCase()
  
  // Build a map of locations with their children
  const nodeMap = new Map<number, TreeNode>()
  const rootNodes: TreeNode[] = []

  // First pass: create all nodes
  locations.forEach(loc => {
    const stockCount = getLocationStockCount(loc.id)
    nodeMap.set(loc.id, {
      key: String(loc.id),
      label: loc.name,
      data: { ...loc, stockCount },
      children: []
    })
  })

  // Second pass: build tree structure
  locations.forEach(loc => {
    const node = nodeMap.get(loc.id)!
    if (loc.parent) {
      const parentNode = nodeMap.get(loc.parent)
      if (parentNode) {
        parentNode.children!.push(node)
      } else {
        rootNodes.push(node)
      }
    } else {
      rootNodes.push(node)
    }
  })

  // Filter by search query if present
  if (query) {
    const filterTree = (nodes: TreeNode[]): TreeNode[] => {
      return nodes.filter(node => {
        const matchesSelf = node.label.toLowerCase().includes(query)
        const filteredChildren = filterTree(node.children || [])
        node.children = filteredChildren
        return matchesSelf || filteredChildren.length > 0
      })
    }
    return filterTree(rootNodes)
  }

  return rootNodes
})

// Get stocks for selected location
const locationStocks = computed((): Stock[] => {
  if (!selectedLocation.value) return []
  return inventoryStore.stocks.filter(s => s.location === selectedLocation.value!.id && s.quantity > 0)
})

// Functions
function getLocationStockCount(locationId: number): number {
  return inventoryStore.stocks
    .filter(s => s.location === locationId)
    .reduce((sum, s) => sum + s.quantity, 0)
}

function selectLocation(location: StorageLocation) {
  selectedLocation.value = location
  selectedTreeKey.value = { [String(location.id)]: true }
}

function onNodeSelect(node: PrimeTreeNode) {
  if (node.data) {
    selectedLocation.value = node.data as StorageLocation
  }
}

// Watch for tree selection changes
watch(selectedTreeKey, (newVal) => {
  const selectedKey = Object.keys(newVal).find(k => newVal[k])
  if (selectedKey) {
    const location = inventoryStore.locations.find(l => l.id === Number(selectedKey))
    if (location) {
      selectedLocation.value = location
    }
  }
})

// Location CRUD
function openCreateLocationDialog(parentId: number | null) {
  editingLocation.value = null
  defaultParentId.value = parentId
  showLocationDialog.value = true
}

function openEditLocationDialog(location: StorageLocation) {
  editingLocation.value = location
  defaultParentId.value = null
  showLocationDialog.value = true
}

function confirmDeleteLocation(location: StorageLocation) {
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

  // Check for child locations
  const hasChildren = storageLocations.value.some(l => l.parent === location.id)
  if (hasChildren) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: `Der Lagerort "${location.name}" enthält Unterordner und kann nicht gelöscht werden.`,
      life: 5000
    })
    return
  }

  confirm.require({
    group: 'location',
    message: `Möchten Sie den Lagerort "${location.name}" wirklich löschen?`,
    header: 'Lagerort löschen',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    acceptLabel: 'Löschen',
    rejectLabel: 'Abbrechen',
    accept: async () => {
      try {
        await inventoryStore.deleteLocation(location.id)
        selectedLocation.value = null
        selectedTreeKey.value = {}
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
  editingLocation.value = null
  defaultParentId.value = null
}

// Transaction dialogs
function openAddStockDialog() {
  transactionType.value = 'IN'
  selectedStock.value = undefined
  showTransactionDialog.value = true
}

function openLoanDialog(stock: Stock) {
  transactionType.value = 'LOAN'
  selectedStock.value = stock
  showTransactionDialog.value = true
}

function openReturnDialog(stock: Stock) {
  transactionType.value = 'RETURN'
  selectedStock.value = stock
  showTransactionDialog.value = true
}

function openMoveDialog(stock: Stock) {
  transactionType.value = 'MOVE'
  selectedStock.value = stock
  showTransactionDialog.value = true
}

function onTransactionComplete() {
  showTransactionDialog.value = false
  selectedStock.value = undefined
}

// Drag and Drop
function onDragStart(event: DragEvent, stock: Stock) {
  draggedStock.value = stock
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', JSON.stringify(stock))
  }
}

function onDragEnd() {
  draggedStock.value = null
  dropTarget.value = null
}

function onDragOver(event: DragEvent, node: PrimeTreeNode | { key: string | number; data: StorageLocation }) {
  if (!draggedStock.value) return
  const nodeData = node.data as StorageLocation | undefined
  if (!nodeData) return
  if (draggedStock.value.location === nodeData.id) return // Can't drop on same location
  
  event.preventDefault()
  dropTarget.value = String(node.key)
}

function onDragLeave() {
  dropTarget.value = null
}

async function onDropOnLocation(event: DragEvent, node: PrimeTreeNode | { key: string | number; data: StorageLocation }) {
  event.preventDefault()
  dropTarget.value = null
  
  if (!draggedStock.value) return
  const targetLocation = node.data as StorageLocation | undefined
  if (!targetLocation) return
  if (draggedStock.value.location === targetLocation.id) return

  const sourceLocation = inventoryStore.locations.find(l => l.id === draggedStock.value!.location)

  // Determine transaction type based on locations
  let type: TransactionType = 'MOVE'
  if (sourceLocation?.is_member && !targetLocation.is_member) {
    type = 'RETURN'
  } else if (!sourceLocation?.is_member && targetLocation.is_member) {
    type = 'LOAN'
  }

  try {
    await inventoryStore.createTransaction({
      transaction_type: type,
      item: draggedStock.value.item || undefined,
      item_variant: draggedStock.value.item_variant || undefined,
      source: draggedStock.value.location,
      target: targetLocation.id,
      quantity: draggedStock.value.quantity,
      note: `Verschoben per Drag & Drop`
    })

    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: `${draggedStock.value.display_name} wurde nach ${targetLocation.name} verschoben`,
      life: 3000
    })
  } catch (err) {
    const errorMessage = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Verschieben fehlgeschlagen'
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: errorMessage,
      life: 5000
    })
  }

  draggedStock.value = null
}

// Initialize
onMounted(async () => {
  // Ensure data is loaded
  if (inventoryStore.locations.length === 0) {
    await inventoryStore.fetchLocations()
  }
  if (inventoryStore.stocks.length === 0) {
    await inventoryStore.fetchStocks()
  }
})
</script>

<style scoped>
.location-file-browser {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 1rem;
}

.browser-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--surface-border);
}

.browser-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.browser-content {
  display: flex;
  gap: 1rem;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* Sidebar */
.browser-sidebar {
  width: 280px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: var(--surface-card);
  border-radius: var(--border-radius);
  padding: 0.75rem;
  overflow: hidden;
}

.sidebar-tabs {
  display: flex;
  gap: 0.5rem;
}

.sidebar-tabs .p-button {
  flex: 1;
}

.sidebar-search {
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--surface-border);
}

.sidebar-tree {
  flex: 1;
  overflow-y: auto;
}

.location-tree {
  padding: 0;
  background: transparent;
}

.location-tree :deep(.p-tree-node-content) {
  padding: 0.25rem 0.5rem;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem;
  border-radius: var(--border-radius);
  transition: background 0.2s;
}

.tree-node.drop-target {
  background: color-mix(in srgb, var(--primary-color) 20%, transparent);
  outline: 2px dashed var(--primary-color);
}

.tree-node i {
  color: var(--primary-color);
}

.node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.add-root-location {
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-border);
}

/* Member list */
.sidebar-members {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: background 0.2s;
}

.member-item:hover {
  background: var(--surface-hover);
}

.member-item.selected {
  background: color-mix(in srgb, var(--primary-color) 15%, transparent);
}

.member-item i {
  color: var(--primary-color);
}

.member-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-members {
  padding: 1rem;
  text-align: center;
  color: var(--text-color-secondary);
}

/* Detail Panel */
.browser-detail {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--surface-card);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border);
  gap: 1rem;
}

.location-info {
  flex: 1;
  min-width: 0;
}

.location-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.location-title i {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.location-title h4 {
  margin: 0;
  font-size: 1.1rem;
}

.location-path {
  display: block;
  font-size: 0.85rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.location-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.content-title {
  font-weight: 600;
  color: var(--text-color-secondary);
}

/* Stock Table */
.stock-table {
  font-size: 0.9rem;
}

.article-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: grab;
}

.article-cell:active {
  cursor: grabbing;
}

.drag-handle {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
}

/* Empty states */
.empty-stock,
.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-color-secondary);
  text-align: center;
}

.empty-stock i,
.no-selection i {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-stock p,
.no-selection p {
  margin: 0 0 1rem;
}

.w-full {
  width: 100%;
}

/* Responsive */
@media (max-width: 768px) {
  .browser-content {
    flex-direction: column;
  }

  .browser-sidebar {
    width: 100%;
    min-width: auto;
    max-height: 300px;
  }
}
</style>
