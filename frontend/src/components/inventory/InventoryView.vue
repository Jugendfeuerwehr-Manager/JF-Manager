<template>
  <div class="inventory-view">
    <OverviewHeader title="Inventar" subtitle="Bestand, Ausgabe und Rücknahme von Material">
      <template #meta>
        <span class="inventory-meta">{{ totalStock }} Teile im Bestand · {{ itemsOnLoan }} ausgegeben</span>
      </template>
      <template #actions>
        <Button label="Rücknahme" icon="pi pi-replay" severity="secondary" outlined @click="showQuickReturnDialog = true" />
        <Button label="Ausgeben" icon="pi pi-user-plus" @click="navigateToTab('lending')" />
      </template>
    </OverviewHeader>

    <div class="inventory-tabs" role="tablist" aria-label="Inventarbereiche" @keydown.left.prevent="moveTab(-1)" @keydown.right.prevent="moveTab(1)">
      <button
        v-for="(tab, index) in tabs"
        :id="`inventory-tab-${tab.name}`"
        :key="tab.name"
        type="button"
        role="tab"
        class="inventory-tab"
        :aria-selected="activeTab === index"
        :tabindex="activeTab === index ? 0 : -1"
        aria-controls="inventory-panel"
        @click="activeTab = index"
      >
        <i :class="tab.icon" aria-hidden="true"></i>{{ tab.label }}<span v-if="tab.count" class="inventory-tab__count">{{ tab.count }}</span>
      </button>
    </div>

    <div id="inventory-panel" role="tabpanel" :aria-labelledby="`inventory-tab-${tabNames[activeTab]}`" class="inventory-panel">
      <InventoryDashboard v-if="activeTab === 0" @navigate="navigateToTab" />
      <LendingWorkbench v-else-if="activeTab === 1" />
      <MemberLoansList v-else-if="activeTab === 2" />
      <StockOverview v-else-if="activeTab === 3" />
      <ItemsManagement v-else-if="activeTab === 4" />
      <LocationFileBrowser v-else-if="activeTab === 5" />
      <CategoriesManagement v-else-if="activeTab === 6" />
      <TransactionsHistory v-else-if="activeTab === 7" />
      <InventoryOrdersTab v-else-if="activeTab === 8" />
    </div>

    <!-- Global Transaction Dialog -->
    <TransactionDialog
      v-model="showTransactionDialog"
      @success="onTransactionSuccess"
    />

    <!-- Quick Return Dialog -->
    <QuickReturnDialog
      v-model="showQuickReturnDialog"
      @success="onTransactionSuccess"
    />

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'

// Organisms
import MemberLoansList from '@/components/inventory/organisms/MemberLoansList.vue'
import StockOverview from '@/components/inventory/organisms/StockOverview.vue'
import ItemsManagement from '@/components/inventory/organisms/ItemsManagement.vue'
import LocationFileBrowser from '@/components/inventory/organisms/LocationFileBrowser.vue'
import CategoriesManagement from '@/components/inventory/organisms/CategoriesManagement.vue'
import TransactionsHistory from '@/components/inventory/organisms/TransactionsHistory.vue'
import TransactionDialog from '@/components/inventory/molecules/TransactionDialog.vue'
import QuickReturnDialog from '@/components/inventory/molecules/QuickReturnDialog.vue'
import InventoryDashboard from '@/components/inventory/organisms/InventoryDashboard.vue'
import LendingWorkbench from '@/components/inventory/organisms/LendingWorkbench.vue'
import InventoryOrdersTab from '@/components/inventory/organisms/InventoryOrdersTab.vue'

import { useInventoryStore } from '@/stores/inventory'
import { useToast } from 'primevue/usetoast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const inventoryStore = useInventoryStore()

interface Props {
  initialTab?: string
}
const props = withDefaults(defineProps<Props>(), { initialTab: undefined })

// Tab name mapping for URL routing
const tabNames = ['overview', 'lending', 'loans', 'stock', 'items', 'locations', 'categories', 'history', 'orders']

function resolveInitialTabIndex(): number {
  const queryTab = route.query.tab
  if (typeof queryTab === 'string') {
    const idx = tabNames.indexOf(queryTab)
    if (idx >= 0) return idx
  }
  if (props.initialTab) {
    const idx = tabNames.indexOf(props.initialTab)
    if (idx >= 0) return idx
  }
  return 0
}

const activeTab = ref(resolveInitialTabIndex())
const showTransactionDialog = ref(false)
const showQuickReturnDialog = ref(false)

// Computed
const totalStock = computed(() => {
  return inventoryStore.stocks.reduce((sum, s) => sum + s.quantity, 0)
})

const itemsOnLoan = computed(() => {
  return inventoryStore.memberLoans.reduce((sum, loan) => sum + loan.total_items, 0)
})

const memberLoansCount = computed(() => {
  return inventoryStore.memberLoans.length
})

const tabs = computed(() => [
  { name: 'overview', label: 'Übersicht', icon: 'pi pi-home' },
  { name: 'lending', label: 'Ausgabe', icon: 'pi pi-user-plus' },
  { name: 'loans', label: 'Ausgegeben', icon: 'pi pi-users', count: memberLoansCount.value },
  { name: 'stock', label: 'Bestand', icon: 'pi pi-box' },
  { name: 'items', label: 'Artikel', icon: 'pi pi-list' },
  { name: 'locations', label: 'Lagerorte', icon: 'pi pi-map-marker' },
  { name: 'categories', label: 'Kategorien', icon: 'pi pi-tags' },
  { name: 'history', label: 'Verlauf', icon: 'pi pi-history' },
  { name: 'orders', label: 'Bestellungen', icon: 'pi pi-shopping-cart' },
])

function moveTab(step: number) {
  activeTab.value = (activeTab.value + step + tabs.value.length) % tabs.value.length
  document.getElementById(`inventory-tab-${tabNames[activeTab.value]}`)?.focus()
}

// Watch route for tab changes
watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && typeof newTab === 'string') {
      const tabIndex = tabNames.indexOf(newTab)
      if (tabIndex >= 0) {
        activeTab.value = tabIndex
      }
    }
  },
  { immediate: true }
)

// Update URL when tab changes
watch(activeTab, (newIndex) => {
  const tabName = tabNames[newIndex] || 'overview'
  if (route.query.tab !== tabName) {
    router.replace({ query: { ...route.query, tab: tabName } })
  }
})

function navigateToTab(tabName: string) {
  const index = tabNames.indexOf(tabName)
  if (index >= 0) {
    activeTab.value = index
  }
}

function onTransactionSuccess() {
  showTransactionDialog.value = false
  showQuickReturnDialog.value = false
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: 'Transaktion wurde erfolgreich durchgeführt',
    life: 3000
  })
}

onMounted(async () => {
  try {
    await inventoryStore.loadEssentialData()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Inventardaten konnten nicht geladen werden',
      life: 5000
    })
  }
})
</script>

<style scoped>
.inventory-view {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.inventory-view :deep(.overview-header) {
  margin-bottom: 0;
  padding-bottom: 0;
}

.inventory-meta {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.inventory-tabs {
  display: flex;
  gap: 2px;
  overflow-x: auto;
  border-bottom: 1px solid var(--jf-color-border);
  scrollbar-width: thin;
}

.inventory-tab {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-2);
  border: 0;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--jf-color-text-muted);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  white-space: nowrap;
  cursor: pointer;
}

.inventory-tab:hover {
  color: var(--jf-color-text);
  background: var(--surface-hover);
}

.inventory-tab[aria-selected='true'] {
  border-bottom-color: var(--jf-color-primary);
  color: var(--jf-color-text);
}

.inventory-tab i {
  font-size: 0.85rem;
}

.inventory-tab__count {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--jf-color-text);
  font-size: var(--jf-text-xs);
}

@media (max-width: 767px) {
  .inventory-tab {
    padding: 0 var(--jf-space-1-5);
  }
}
</style>
