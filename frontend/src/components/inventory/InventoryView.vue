<template>
  <div class="inventory-view">
    <OverviewHeader
      title="Inventar & Ausleihen"
      subtitle="Bestandsverwaltung und Ausleihen für die Jugendfeuerwehr"
    >
      <template #meta>
        <Tag severity="info" :value="`${totalStock} Artikel insgesamt`" />
        <Tag severity="warning" :value="`${itemsOnLoan} ausgeliehen`" />
      </template>
      <template #actions>
        <Button
          label="Ausleihen"
          icon="pi pi-user"
          severity="primary"
          @click="showQuickLoanDialog = true"
        />
        <Button
          label="Rückgabe"
          icon="pi pi-replay"
          severity="success"
          @click="showQuickReturnDialog = true"
        />
      </template>
    </OverviewHeader>

    <!-- Navigation Tabs -->
    <TabView v-model:active-index="activeTab" class="inventory-tabs">
      <!-- Dashboard / Quick Overview -->
      <TabPanel :value="0">
        <template #header>
          <i class="pi pi-home tab-icon"></i>
          <span>Übersicht</span>
        </template>
        <InventoryDashboard @navigate="navigateToTab" />
      </TabPanel>

      <!-- Member Loans -->
      <TabPanel :value="1">
        <template #header>
          <i class="pi pi-users tab-icon"></i>
          <span>Ausleihen</span>
          <Badge v-if="memberLoansCount > 0" :value="memberLoansCount" severity="info" class="ml-2" />
        </template>
        <MemberLoansList />
      </TabPanel>

      <!-- Stock Overview -->
      <TabPanel :value="2">
        <template #header>
          <i class="pi pi-box tab-icon"></i>
          <span>Bestand</span>
        </template>
        <StockOverview />
      </TabPanel>

      <!-- Items Management -->
      <TabPanel :value="3">
        <template #header>
          <i class="pi pi-list tab-icon"></i>
          <span>Artikel</span>
        </template>
        <ItemsManagement />
      </TabPanel>

      <!-- Locations Management -->
      <TabPanel :value="4">
        <template #header>
          <i class="pi pi-map-marker tab-icon"></i>
          <span>Lagerorte</span>
        </template>
        <LocationFileBrowser />
      </TabPanel>

      <!-- Categories Management -->
      <TabPanel :value="5">
        <template #header>
          <i class="pi pi-tags tab-icon"></i>
          <span>Kategorien</span>
        </template>
        <CategoriesManagement />
      </TabPanel>

      <!-- Transactions History -->
      <TabPanel :value="6">
        <template #header>
          <i class="pi pi-history tab-icon"></i>
          <span>Verlauf</span>
        </template>
        <TransactionsHistory />
      </TabPanel>
    </TabView>

    <!-- Global Transaction Dialog -->
    <TransactionDialog
      v-model="showTransactionDialog"
      @success="onTransactionSuccess"
    />

    <!-- Quick Loan Dialog -->
    <QuickLoanDialog
      v-model="showQuickLoanDialog"
      @success="onTransactionSuccess"
    />

    <!-- Quick Return Dialog -->
    <QuickReturnDialog
      v-model="showQuickReturnDialog"
      @success="onTransactionSuccess"
    />

    <!-- Toast for notifications -->
    <Toast />
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import OverviewHeader from '@/components/layout/OverviewHeader.vue'

// Organisms
import MemberLoansList from '@/components/inventory/organisms/MemberLoansList.vue'
import StockOverview from '@/components/inventory/organisms/StockOverview.vue'
import ItemsManagement from '@/components/inventory/organisms/ItemsManagement.vue'
import LocationFileBrowser from '@/components/inventory/organisms/LocationFileBrowser.vue'
import CategoriesManagement from '@/components/inventory/organisms/CategoriesManagement.vue'
import TransactionsHistory from '@/components/inventory/organisms/TransactionsHistory.vue'
import TransactionDialog from '@/components/inventory/molecules/TransactionDialog.vue'
import QuickLoanDialog from '@/components/inventory/molecules/QuickLoanDialogV2.vue'
import QuickReturnDialog from '@/components/inventory/molecules/QuickReturnDialog.vue'
import InventoryDashboard from '@/components/inventory/organisms/InventoryDashboard.vue'

import { useInventoryStore } from '@/stores/inventory'
import { useToast } from 'primevue/usetoast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const inventoryStore = useInventoryStore()

const activeTab = ref(0)
const showTransactionDialog = ref(false)
const showQuickLoanDialog = ref(false)
const showQuickReturnDialog = ref(false)

// Tab name mapping for URL routing
const tabNames = ['overview', 'loans', 'stock', 'items', 'locations', 'categories', 'history']

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
  showQuickLoanDialog.value = false
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
  } catch (error) {
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
  padding: 0;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.inventory-tabs {
  margin-top: 1rem;
}

.inventory-tabs :deep(.p-tabview-nav) {
  border-bottom: 2px solid var(--surface-border);
  gap: 0;
}

.inventory-tabs :deep(.p-tabview-nav-link) {
  padding: 1rem 1.25rem;
  border: none;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s ease;
}

.inventory-tabs :deep(.p-tabview-nav-link:hover) {
  background: var(--surface-hover);
}

.inventory-tabs :deep(.p-highlight .p-tabview-nav-link) {
  border-bottom-color: var(--primary-color);
  background: transparent;
}

.inventory-tabs :deep(.p-tabview-panels) {
  padding: 1.5rem 0;
  background: transparent;
}

.tab-icon {
  margin-right: 0.5rem;
}

.ml-2 {
  margin-left: 0.5rem;
}

@media (max-width: 768px) {
  .inventory-tabs :deep(.p-tabview-nav) {
    flex-wrap: wrap;
  }

  .inventory-tabs :deep(.p-tabview-nav-link) {
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
  }

  .tab-icon {
    margin-right: 0.25rem;
  }
}
</style>
