<template>



  <div class="order-detail-view">
    <ProgressSpinner v-if="loading" />

    <Message v-else-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <div v-else-if="order">
      <!-- Header -->
        <Toolbar>
          <template #start>
            <div class="flex gap-2">
              
            </div>
            <Button 
              icon="pi pi-arrow-left" 
              severity="secondary"
              text
              @click="router.push({ name: 'orders' })"
              v-tooltip.top="'Zurück zur Übersicht'"
            />
            <h4>Bestellung #{{ order?.id }} </h4>
            
          </template>

          <template #end>
            <div class="flex gap-2">
              
              <Button 
                label="Bearbeiten" 
                icon="pi pi-pencil" 
                @click="$emit('edit', order.id)"
              />
              <Button 
                label="Löschen" 
                icon="pi pi-trash" 
                severity="danger"
                @click="confirmDelete"
              />
            </div>
          </template>
      </Toolbar>

      <!-- Info Grid -->
      <div class="grid mb-4">
        <div class="col-12 md:col-6">
          <Card>
            <template #title>Details</template>
            <template #content>
              <div class="mb-2"><strong>Status:</strong> {{ order.common_status?.name }}</div>
              <div class="mb-2"><strong>Besteller:</strong> {{ order.member_name }}</div>
              <div class="mb-2"><strong>Gruppe:</strong> {{ order.member_group }}</div>
              <div class="mb-2"><strong>Datum:</strong> {{ formatDate(order.order_date) }}</div>
              <div v-if="order.notes"><strong>Notizen:</strong> {{ order.notes }}</div>
              <div class="mb-2"><strong>Artikel:</strong> {{ order.items_count }}</div>
              <div class="mb-2"><strong>Gesamtmenge:</strong> {{ totalQuantity }}</div>
            </template>
          </Card>
        </div>

      </div>

      <!-- Items Table -->
      <Card>
        <template #title>
          <div class="flex justify-content-between align-items-center">
            <span>Artikel</span>
            <div v-if="allowedNextStatuses.length > 0" class="flex gap-2">
              <Dropdown
                v-model="quickStatusId"
                :options="allowedNextStatuses"
                optionLabel="name"
                optionValue="id"
                placeholder="Alle Status ändern..."
                class="w-15rem"
                :showClear="true"
                @change="handleQuickStatusChange"
              />
            </div>
            <div v-else class="text-sm text-500">
              Keine Status-Änderungen möglich
            </div>
          </div>
        </template>
        <template #content>
          <DataTable :value="order.items" stripedRows>
            <Column field="item_name" header="Artikel">
              <template #body="{ data }">
                <div>
                  <strong>{{ data.item_name }}</strong>
                  <div v-if="data.item_details?.category" class="text-sm text-500">
                    {{ data.item_details.category }}
                  </div>
                </div>
              </template>
            </Column>
            <Column field="size" header="Größe">
              <template #body="{ data }">
                <Badge v-if="data.size" :value="data.size" severity="secondary" />
                <span v-else class="text-500">-</span>
              </template>
            </Column>
            <Column field="quantity" header="Menge" style="width: 80px" />
            <Column header="Status" style="width: 150px">
              <template #body="{ data }">
                <Tag 
                  :value="data.status_details.name"
                  :style="{ backgroundColor: data.status_details.color, color: 'white' }"
                />
              </template>
            </Column>
            <Column header="Eingang" style="width: 150px">
              <template #body="{ data }">
                <span v-if="data.received_date" class="text-sm">
                  {{ formatDate(data.received_date) }}
                </span>
                <span v-else class="text-500">-</span>
              </template>
            </Column>
            <Column header="Ausgabe" style="width: 150px">
              <template #body="{ data }">
                <span v-if="data.delivered_date" class="text-sm">
                  {{ formatDate(data.delivered_date) }}
                </span>
                <span v-else class="text-500">-</span>
              </template>
            </Column>
            <Column header="Aktionen" style="width: 100px">
              <template #body="{ data }">
                <Button
                  icon="pi pi-pencil"
                  severity="warning"
                  text
                  rounded
                  @click="openStatusDialog(data)"
                  v-tooltip.top="'Status ändern'"
                />
              </template>
            </Column>
            <template #expansion="{ data }">
              <div v-if="data.notes" class="p-3 bg-primary-50">
                <div class="flex align-items-center gap-2">
                  <i class="pi pi-comment text-primary"></i>
                  <strong>Notiz:</strong>
                  <span>{{ data.notes }}</span>
                </div>
              </div>
            </template>
          </DataTable>
        </template>
      </Card>
    </div>

    <!-- Status Update Dialog -->
        <!-- Update Status Dialog -->
    <UpdateItemStatusDialog
      v-if="selectedItem"
      :visible="statusDialogVisible"
      :item="selectedItem"
      :status-options="statusOptions"
      @update:visible="statusDialogVisible = $event"
      @status-updated="handleStatusUpdated"
    />

    <!-- Send Summary Dialog -->
    
    
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Dropdown from 'primevue/dropdown'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useOrdersStore } from '@/stores/orders'
import { useOrderStatusStore } from '@/stores/orderStatus'
import { orderItemsApi } from '@/api/orderItems'
import UpdateItemStatusDialog from './molecules/UpdateItemStatusDialog.vue'
import type { OrderItem } from '@/types/orders'
import { Toolbar } from 'primevue'

interface Props {
  orderId: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  edit: [orderId: number]
  deleted: []
}>()

const router = useRouter()
const ordersStore = useOrdersStore()
const statusStore = useOrderStatusStore()
const confirm = useConfirm()
const toast = useToast()

const loading = ref(false)
const error = ref<string | null>(null)
const order = computed(() => ordersStore.currentOrder)
const statusOptions = computed(() => statusStore.statuses || [])

// Status dialog
const statusDialogVisible = ref(false)
const selectedItem = ref<OrderItem | null>(null)
const quickStatusId = ref<number | null>(null)

// Send summary dialog
const showSendSummaryDialog = ref(false)
const sendSummaryEmail = ref('')
const sendingSummary = ref(false)

const totalQuantity = computed(() => {
  return order.value?.items?.reduce((sum: number, item: any) => sum + item.quantity, 0) || 0
})

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('de-DE')
}

async function loadOrder() {
  loading.value = true
  error.value = null
  
  try {
    await Promise.all([
      ordersStore.fetchOrder(props.orderId, true),
      statusStore.fetchActiveStatuses()
    ])
  } catch (e: any) {
    error.value = e.message || 'Fehler beim Laden'
  } finally {
    loading.value = false
  }
}

function openStatusDialog(item: OrderItem) {
  selectedItem.value = item
  statusDialogVisible.value = true
}

async function handleStatusUpdated() {
  // Reload order to show updated status
  await loadOrder()
  toast.add({
    severity: 'success',
    summary: 'Erfolg',
    detail: 'Status wurde aktualisiert',
    life: 3000
  })
}

// Get allowed next statuses based on current item statuses
const allowedNextStatuses = computed(() => {
  if (!order.value || !order.value.items || order.value.items.length === 0) {
    return []
  }
  
  // Get all unique current statuses
  const currentStatusCodes = new Set(
    order.value.items.map((item: any) => item.status_code)
  )
  
  // Define workflow transitions
  const transitions: Record<string, string[]> = {
    'NEW': ['ORDERED', 'CANCELLED'],
    'ORDERED': ['RECEIVED', 'CANCELLED'],
    'RECEIVED': ['DELIVERED', 'CANCELLED'],
    'DELIVERED': [],
    'CANCELLED': []
  }
  
  // Find common next statuses across all current statuses
  let commonNextStatuses: string[] | null = null
  
  for (const code of currentStatusCodes) {
    const nextStatuses = transitions[code] || []
    if (commonNextStatuses === null) {
      commonNextStatuses = [...nextStatuses]
    } else {
      // Keep only statuses that are common
      commonNextStatuses = commonNextStatuses.filter(s => nextStatuses.includes(s))
    }
  }
  
  // Filter statusOptions to only allowed statuses
  const allowedCodes = commonNextStatuses || []
  return statusOptions.value.filter(status => allowedCodes.includes(status.code))
})

async function handleQuickStatusChange() {
  if (!quickStatusId.value || !order.value) return
  
  confirm.require({
    message: `Alle ${order.value.items.length} Artikel auf den ausgewählten Status setzen?`,
    header: 'Status ändern',
    icon: 'pi pi-question-circle',
    acceptLabel: 'Ja',
    rejectLabel: 'Nein',
    accept: async () => {
      try {
        const itemIds = order.value!.items.map((item: any) => item.id)
        
        await orderItemsApi.bulkUpdateStatus({
          item_ids: itemIds,
          status: quickStatusId.value!,
          notes: 'Bulk-Status-Änderung über Bestelldetails'
        })
        
        toast.add({
          severity: 'success',
          summary: 'Erfolg',
          detail: `Status von ${itemIds.length} Artikeln wurde aktualisiert`,
          life: 3000
        })
        
        // Reload order
        await loadOrder()
        quickStatusId.value = null
      } catch (e: any) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: e.message || 'Status konnte nicht aktualisiert werden',
          life: 3000
        })
      }
    },
    reject: () => {
      quickStatusId.value = null
    }
  })
}

async function handleSendSummary() {
  if (!sendSummaryEmail.value || !order.value) return
  
  sendingSummary.value = true
  
  try {
    const { ordersApi } = await import('@/api/orders')
    
    // Get all unique status IDs from order items
    const statusIds = [...new Set(order.value.items.map((item: any) => item.status))]
    
    await ordersApi.sendSummary({
      recipient_email: sendSummaryEmail.value,
      status_filter: statusIds,
      include_notes: true,
      group_by_category: true
    })
    
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: `Bestellübersicht wurde an ${sendSummaryEmail.value} gesendet`,
      life: 5000
    })
    
    showSendSummaryDialog.value = false
    sendSummaryEmail.value = ''
    
    // Reload order (status might have changed from NEW to ORDERED)
    await loadOrder()
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: e.message || 'Fehler beim Versenden der E-Mail',
      life: 5000
    })
  } finally {
    sendingSummary.value = false
  }
}

function confirmDelete() {
  confirm.require({
    message: 'Bestellung wirklich löschen?',
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Ja',
    rejectLabel: 'Nein',
    accept: async () => {
      try {
        await ordersStore.deleteOrder(props.orderId)
        toast.add({
          severity: 'success',
          summary: 'Gelöscht',
          detail: 'Bestellung wurde gelöscht',
          life: 3000
        })
        emit('deleted')
      } catch (e: any) {
        toast.add({
          severity: 'error',
          summary: 'Fehler',
          detail: e.message,
          life: 3000
        })
      }
    }
  })
}

onMounted(() => {
  loadOrder()
})
</script>

<style scoped>
.order-detail-view {
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
