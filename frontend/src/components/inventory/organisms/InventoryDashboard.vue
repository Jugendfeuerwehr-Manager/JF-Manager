<template>
  <div class="inventory-dashboard">
    <section class="kpi-grid" aria-label="Kennzahlen">
      <button v-for="tile in tiles" :key="tile.tab" type="button" class="kpi-tile" @click="$emit('navigate', tile.tab)">
        <span class="kpi-tile__label">{{ tile.label }}<i :class="tile.icon" aria-hidden="true"></i></span>
        <span class="kpi-tile__value">{{ tile.value }}</span>
        <span class="kpi-tile__cta">{{ tile.cta }}<i class="pi pi-arrow-right" aria-hidden="true"></i></span>
      </button>
    </section>

    <section class="panel" aria-labelledby="quick-actions-title">
      <h2 id="quick-actions-title">Schnellaktionen</h2>
      <div class="quick-actions">
        <Button label="Ausgeben" icon="pi pi-user-plus" @click="$emit('navigate', 'lending')" />
        <Button label="Rücknahme" icon="pi pi-replay" severity="secondary" outlined @click="showQuickReturnDialog = true" />
        <Button label="Wareneingang" icon="pi pi-arrow-down" severity="secondary" outlined @click="openTransactionDialog('IN')" />
        <Button label="Umlagern" icon="pi pi-arrows-h" severity="secondary" outlined @click="openTransactionDialog('MOVE')" />
      </div>
    </section>

    <div class="panel-grid">
      <section class="panel" aria-labelledby="low-stock-title">
        <header class="panel__header">
          <h2 id="low-stock-title">Niedriger Bestand</h2>
          <button type="button" class="text-link" @click="$emit('navigate', 'stock')">Bestand</button>
        </header>
        <ul v-if="lowStockItems.length" class="rows">
          <li v-for="item in lowStockItems" :key="item.id" class="row">
            <span class="row__text">
              <span class="row__title">{{ item.variant_display || item.item_name }}</span>
              <span class="row__meta">{{ item.location_name }}</span>
            </span>
            <StockBadge :quantity="item.quantity" />
          </li>
        </ul>
        <p v-else class="empty"><i class="pi pi-check-circle" aria-hidden="true"></i>Alle Bestände ausreichend</p>
      </section>

      <section class="panel" aria-labelledby="loans-title">
        <header class="panel__header">
          <h2 id="loans-title">Ausgegeben an</h2>
          <button type="button" class="text-link" @click="$emit('navigate', 'loans')">Alle</button>
        </header>
        <ul v-if="recentLoans.length" class="rows">
          <li v-for="loan in recentLoans" :key="loan.member_id" class="row">
            <span class="row__avatar" aria-hidden="true">{{ getInitials(loan.member_name) }}</span>
            <span class="row__text">
              <span class="row__title">{{ loan.member_name }}</span>
              <span class="row__meta">{{ loan.total_items }} {{ loan.total_items === 1 ? 'Teil' : 'Teile' }}</span>
            </span>
          </li>
        </ul>
        <p v-else class="empty"><i class="pi pi-inbox" aria-hidden="true"></i>Nichts ausgegeben</p>
      </section>

      <section class="panel" aria-labelledby="transactions-title">
        <header class="panel__header">
          <h2 id="transactions-title">Letzte Buchungen</h2>
          <button type="button" class="text-link" @click="$emit('navigate', 'history')">Verlauf</button>
        </header>
        <ul v-if="recentTransactions.length" class="rows">
          <li v-for="tx in recentTransactions" :key="tx.id" class="row">
            <TransactionTypeBadge :type="tx.transaction_type" />
            <span class="row__text">
              <span class="row__title">{{ tx.item_name }}</span>
              <span class="row__meta">{{ formatDate(tx.date) }}</span>
            </span>
            <span class="row__qty">{{ tx.quantity }}×</span>
          </li>
        </ul>
        <p v-else class="empty"><i class="pi pi-inbox" aria-hidden="true"></i>Noch keine Buchungen</p>
      </section>
    </div>

    <TransactionDialog
      v-model="showTransactionDialog"
      :initial-type="transactionType"
      @success="onTransactionSuccess"
    />

    <QuickReturnDialog
      v-model="showQuickReturnDialog"
      @success="onTransactionSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Button from 'primevue/button'
import StockBadge from '../atoms/StockBadge.vue'
import TransactionTypeBadge from '../atoms/TransactionTypeBadge.vue'
import TransactionDialog from '../molecules/TransactionDialog.vue'
import QuickReturnDialog from '../molecules/QuickReturnDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { TransactionType } from '@/types/inventory'

defineEmits<{
  navigate: [tab: string]
}>()

const inventoryStore = useInventoryStore()

const showTransactionDialog = ref(false)
const showQuickReturnDialog = ref(false)
const transactionType = ref<TransactionType>('LOAN')

// Computed stats
const totalStock = computed(() => {
  return inventoryStore.stocks.reduce((sum, s) => sum + s.quantity, 0)
})

const itemsOnLoan = computed(() => {
  return inventoryStore.memberLoans.reduce((sum, loan) => sum + loan.total_items, 0)
})

const totalItems = computed(() => inventoryStore.items.length)
const totalLocations = computed(() => inventoryStore.locations.length)

const tiles = computed(() => [
  { tab: 'stock', label: 'Im Bestand', icon: 'pi pi-box', value: totalStock.value, cta: 'Bestand' },
  { tab: 'loans', label: 'Ausgegeben', icon: 'pi pi-users', value: itemsOnLoan.value, cta: 'Ausgaben' },
  { tab: 'items', label: 'Artikel', icon: 'pi pi-list', value: totalItems.value, cta: 'Artikel' },
  { tab: 'locations', label: 'Lagerorte', icon: 'pi pi-map-marker', value: totalLocations.value, cta: 'Lagerorte' },
])

const recentLoans = computed(() => {
  return inventoryStore.memberLoans.slice(0, 5)
})

const lowStockItems = computed(() => {
  return inventoryStore.stocks
    .filter((s) => {
      const location = inventoryStore.locations.find((l) => l.id === s.location)
      return !location?.is_member && s.quantity > 0 && s.quantity <= 5
    })
    .slice(0, 5)
})

const recentTransactions = computed(() => {
  return inventoryStore.transactions.slice(0, 5)
})

function getInitials(name: string): string {
  const parts = name.split(' ')
  const first = parts[0]
  const last = parts[parts.length - 1]
  if (parts.length >= 2 && first && last && first.length > 0 && last.length > 0) {
    return (first.charAt(0) + last.charAt(0)).toUpperCase()
  }
  return name.substring(0, 2).toUpperCase()
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function openTransactionDialog(type: TransactionType) {
  transactionType.value = type
  showTransactionDialog.value = true
}

function onTransactionSuccess() {
  showTransactionDialog.value = false
  showQuickReturnDialog.value = false
}
</script>

<style scoped>
.inventory-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--jf-space-2);
}

.kpi-tile {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: var(--jf-space-1);
  padding: var(--jf-space-2) var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
  color: var(--jf-color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: box-shadow var(--jf-duration), border-color var(--jf-duration);
}

.kpi-tile:hover {
  border-color: var(--p-surface-300);
  box-shadow: var(--jf-shadow-md);
}

.kpi-tile__label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-medium);
  color: var(--jf-color-text-muted);
}

.kpi-tile__value {
  font-size: 2rem;
  font-weight: var(--jf-weight-bold);
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.kpi-tile__cta {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
}

.kpi-tile__cta i {
  font-size: 0.7rem;
}

.panel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--jf-space-2);
  align-items: start;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-2) var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
}

.panel h2 {
  margin: 0;
  font-size: var(--jf-text-md);
  font-weight: var(--jf-weight-semibold);
}

.panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
}

.text-link {
  display: inline-flex;
  align-items: center;
  min-height: var(--jf-touch-target);
  padding: 0;
  border: 0;
  background: none;
  color: var(--jf-color-primary);
  font: inherit;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  cursor: pointer;
}

.rows {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  list-style: none;
}

.row {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1) 0;
  border-top: 1px solid var(--jf-color-border);
}

.row__avatar {
  flex: none;
  display: inline-grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  background: var(--surface-hover);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
}

.row__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.row__title {
  font-weight: var(--jf-weight-semibold);
  font-size: var(--jf-text-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row__meta {
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.row__qty {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 599px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--jf-space-1);
  }

  .kpi-tile,
  .panel {
    padding: var(--jf-space-1-5) var(--jf-space-2);
  }

  .kpi-tile__value {
    font-size: 1.5rem;
  }
}

.empty {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}
</style>
