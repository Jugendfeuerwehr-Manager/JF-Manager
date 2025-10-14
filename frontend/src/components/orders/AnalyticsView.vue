<template>
  <div class="orders-analytics-view">
    <h2 class="mb-4">Bestellungen - Statistiken</h2>

    <!-- Key Metrics -->
    <div class="grid mb-4">
      <div class="col-12 md:col-3">
        <Card>
          <template #content>
            <div class="text-center">
              <div class="text-500 mb-2">Gesamt</div>
              <div class="text-4xl font-bold text-primary">{{ stats?.total_orders || 0 }}</div>
              <div class="text-sm text-500 mt-2">Bestellungen</div>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 md:col-3">
        <Card>
          <template #content>
            <div class="text-center">
              <div class="text-500 mb-2">Offen</div>
              <div class="text-4xl font-bold text-orange-500">{{ pendingCount }}</div>
              <div class="text-sm text-500 mt-2">Artikel offen</div>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 md:col-3">
        <Card>
          <template #content>
            <div class="text-center">
              <div class="text-500 mb-2">Ausgeliefert</div>
              <div class="text-4xl font-bold text-green-500">{{ deliveredCount }}</div>
              <div class="text-sm text-500 mt-2">Artikel ausgeliefert</div>
            </div>
          </template>
        </Card>
      </div>

      <div class="col-12 md:col-3">
        <Card>
          <template #content>
            <div class="text-center">
              <div class="text-500 mb-2">Artikel</div>
              <div class="text-4xl font-bold text-blue-500">{{ stats?.total_items || 0 }}</div>
              <div class="text-sm text-500 mt-2">Gesamt bestellt</div>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Status Distribution -->
    <div class="grid mb-4">
      <div class="col-12 lg:col-6">
        <Card>
          <template #title>Status-Verteilung</template>
          <template #content>
            <DataTable 
              :value="statusDistribution" 
              :rows="10"
            >
              <Column field="status_name" header="Status">
                <template #body="{ data }">
                  <Tag
                    :value="data.status_name"
                    :style="{ backgroundColor: data.status_color }"
                  />
                </template>
              </Column>
              <Column field="count" header="Anzahl" />
              <Column field="percentage" header="Anteil">
                <template #body="{ data }">
                  {{ data.percentage.toFixed(1) }}%
                </template>
              </Column>
            </DataTable>
          </template>
        </Card>
      </div>

      <div class="col-12 lg:col-6">
        <Card>
          <template #title>Top Besteller</template>
          <template #content>
            <DataTable 
              :value="topMembers" 
              :rows="10"
            >
              <Column field="member__name" header="Vorname" />
              <Column field="member__lastname" header="Nachname" />
              <Column field="order_count" header="Bestellungen" />
            </DataTable>
          </template>
        </Card>
      </div>
    </div>

    <!-- Recent Activity -->
    <Card>
      <template #title>Letzte Aktivitäten</template>
      <template #content>
        <DataTable 
          :value="recentOrders" 
          :loading="loading"
          stripedRows
        >
          <Column field="id" header="ID" style="width: 80px" />
          <Column field="member_name" header="Mitglied" />
          <Column field="order_date" header="Datum">
            <template #body="{ data }">
              {{ formatDate(data.order_date) }}
            </template>
          </Column>
          <Column field="items_count" header="Artikel" style="width: 100px" />
          <Column header="Status">
            <template #body="{ data }">
              <Tag
                v-if="data.common_status"
                :value="data.common_status.name"
                :style="{ backgroundColor: data.common_status.color }"
              />
            </template>
          </Column>
          <Column header="Aktionen" style="width: 100px">
            <template #body="{ data }">
              <Button
                icon="pi pi-eye"
                text
                @click="$emit('viewOrder', data.id)"
              />
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import { useOrdersStore } from '@/stores/orders'

const emit = defineEmits<{
  viewOrder: [orderId: number]
}>()

const ordersStore = useOrdersStore()

const loading = ref(false)
const stats = computed(() => ordersStore.statistics)
const recentOrders = computed(() => ordersStore.orders.slice(0, 10))

const statusDistribution = computed(() => {
  if (!stats.value?.status_breakdown) return []
  
  const total = stats.value.status_breakdown.reduce((sum: number, item) => sum + item.count, 0)
  
  return stats.value.status_breakdown.map(item => ({
    status_name: item.status__name,
    status_code: item.status__code,
    status_color: item.status__color,
    count: item.count,
    percentage: total > 0 ? (item.count / total) * 100 : 0
  }))
})

const topMembers = computed(() => {
  return stats.value?.top_members || []
})

const pendingCount = computed(() => {
  return stats.value?.pending_items || 0
})

const deliveredCount = computed(() => {
  return stats.value?.delivered_items || 0
})

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function loadData() {
  loading.value = true
  
  try {
    await Promise.all([
      ordersStore.fetchStatistics(),
      ordersStore.fetchRecentOrders()
    ])
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.orders-analytics-view {
  padding: 1rem;
  max-width: 1400px;
  margin: 0 auto;
}
</style>
