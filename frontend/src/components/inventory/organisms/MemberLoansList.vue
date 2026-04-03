<template>
  <div class="member-loans-list">
    <!-- Header -->
    <div class="list-header">
      <h3>
        <i class="pi pi-users"></i>
        Ausgeliehene Artikel
      </h3>
      <div class="header-actions">
        <IconField>
          <InputIcon class="pi pi-search" />
          <InputText v-model="searchQuery" placeholder="Mitglied suchen..." />
        </IconField>
        <Button
          label="Neue Ausleihe"
          icon="pi pi-plus"
          @click="showLoanDialog = true"
        />
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-cards">
      <Card class="stat-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-users stat-icon"></i>
            <div class="stat-info">
              <span class="stat-value">{{ filteredLoans.length }}</span>
              <span class="stat-label">Mitglieder mit Ausleihen</span>
            </div>
          </div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-content">
            <i class="pi pi-box stat-icon"></i>
            <div class="stat-info">
              <span class="stat-value">{{ totalItemsOnLoan }}</span>
              <span class="stat-label">Artikel ausgeliehen</span>
            </div>
          </div>
        </template>
      </Card>
    </div>

    <!-- Loans List -->
    <div v-if="filteredLoans.length > 0" class="loans-list">
      <MemberLoanCard
        v-for="loan in filteredLoans"
        :key="loan.member_id"
        :loan="loan"
        @return="handleReturn"
        @discard="handleDiscard"
      />
    </div>

    <!-- Empty State -->
    <Card v-else class="empty-state">
      <template #content>
        <div class="empty-content">
          <i class="pi pi-inbox"></i>
          <h4>Keine Ausleihen gefunden</h4>
          <p v-if="searchQuery">Keine Mitglieder gefunden, die "{{ searchQuery }}" entsprechen.</p>
          <p v-else>Es sind derzeit keine Artikel ausgeliehen.</p>
          <Button label="Neue Ausleihe" icon="pi pi-plus" @click="showLoanDialog = true" />
        </div>
      </template>
    </Card>

    <!-- Dialogs -->
    <TransactionDialog
      v-model="showLoanDialog"
      initial-type="LOAN"
      @success="onTransactionSuccess"
    />

    <TransactionDialog
      v-model="showReturnDialog"
      initial-type="RETURN"
      :initial-stock="selectedStock"
      @success="onTransactionSuccess"
    />

    <TransactionDialog
      v-model="showDiscardDialog"
      initial-type="DISCARD"
      :initial-stock="selectedStock"
      @success="onTransactionSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import MemberLoanCard from '../molecules/MemberLoanCard.vue'
import TransactionDialog from '../molecules/TransactionDialog.vue'
import { useInventoryStore } from '@/stores/inventory'
import type { Stock, MemberLoan } from '@/types/inventory'

const inventoryStore = useInventoryStore()

const searchQuery = ref('')
const showLoanDialog = ref(false)
const showReturnDialog = ref(false)
const showDiscardDialog = ref(false)
const selectedStock = ref<Stock | undefined>(undefined)

const filteredLoans = computed(() => {
  if (!searchQuery.value) return inventoryStore.memberLoans
  const query = searchQuery.value.toLowerCase()
  return inventoryStore.memberLoans.filter((loan) =>
    loan.member_name.toLowerCase().includes(query)
  )
})

const totalItemsOnLoan = computed(() => {
  return inventoryStore.memberLoans.reduce((sum, loan) => sum + loan.total_items, 0)
})

function handleReturn(item: MemberLoan['items'][0]) {
  const stock = inventoryStore.stocks.find((s) => s.id === item.stock_id)
  if (stock) {
    selectedStock.value = stock
    showReturnDialog.value = true
  }
}

function handleDiscard(item: MemberLoan['items'][0]) {
  const stock = inventoryStore.stocks.find((s) => s.id === item.stock_id)
  if (stock) {
    selectedStock.value = stock
    showDiscardDialog.value = true
  }
}

function onTransactionSuccess() {
  showLoanDialog.value = false
  showReturnDialog.value = false
  showDiscardDialog.value = false
  selectedStock.value = undefined
}
</script>

<style scoped>
.member-loans-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.list-header h3 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.stats-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.stat-card {
  background: var(--surface-card);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.stat-icon {
  font-size: 2rem;
  color: var(--primary-color);
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-color);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.loans-list {
  display: flex;
  flex-direction: column;
}

.empty-state {
  text-align: center;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 2rem;
}

.empty-content i {
  font-size: 3rem;
  color: var(--text-color-secondary);
}

.empty-content h4 {
  margin: 0;
  color: var(--text-color);
}

.empty-content p {
  margin: 0;
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .list-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    flex-direction: column;
  }
}
</style>
