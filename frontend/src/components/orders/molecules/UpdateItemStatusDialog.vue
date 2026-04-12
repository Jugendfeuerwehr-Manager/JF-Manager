<template>
  <Dialog 
    v-model:visible="isVisible" 
    modal 
    :header="`Status aktualisieren - ${item?.item_name || ''}`"
    :style="{ width: '600px' }"
    @hide="handleClose"
  >
    <div v-if="item" class="status-dialog-content">
      <!-- Current Item Info -->
      <div class="item-info mb-4 p-3 border-round bg-primary-50">
        <div class="flex justify-content-between align-items-center">
          <div>
            <h6 class="m-0 mb-2">{{ item.item_name }}</h6>
            <small class="text-600">{{ item.item_details?.category }} | Anzahl: {{ item.quantity }}</small>
          </div>
          <Tag 
            :value="item.status_name"
            :style="{ backgroundColor: item.status_color, color: 'white' }"
          />
        </div>
        <div v-if="item.size" class="mt-2">
          <Badge :value="`Größe: ${item.size}`" severity="secondary" />
        </div>
      </div>

      <form @submit.prevent="handleSubmit">
        <!-- Status Selection -->
        <div class="field">
          <label for="status" class="font-semibold">Neuer Status *</label>
          <Dropdown
            id="status"
            v-model="formData.status"
            :options="statusOptions"
            optionLabel="name"
            optionValue="id"
            placeholder="Status auswählen"
            class="w-full"
            :class="{ 'p-invalid': submitted && !formData.status }"
          >
            <template #option="{ option }">
              <div class="flex align-items-center gap-2">
                <div 
                  class="status-color-indicator" 
                  :style="{ backgroundColor: option.color }"
                ></div>
                <span>{{ option.name }}</span>
              </div>
            </template>
          </Dropdown>
          <small v-if="submitted && !formData.status" class="p-error">Status ist erforderlich</small>
        </div>

        <!-- Received Date -->
        <div class="field">
          <label for="received_date" class="font-semibold">Eingangsdatum</label>
          <Calendar
            id="received_date"
            v-model="formData.received_date"
            showTime
            hourFormat="24"
            dateFormat="dd.mm.yy"
            class="w-full"
            placeholder="Datum auswählen"
            :showIcon="true"
          />
          <small class="text-500">Wird automatisch gesetzt bei Status "Eingegangen"</small>
        </div>

        <!-- Delivered Date -->
        <div class="field">
          <label for="delivered_date" class="font-semibold">Ausgabedatum</label>
          <Calendar
            id="delivered_date"
            v-model="formData.delivered_date"
            showTime
            hourFormat="24"
            dateFormat="dd.mm.yy"
            class="w-full"
            placeholder="Datum auswählen"
            :showIcon="true"
          />
          <small class="text-500">Wird automatisch gesetzt bei Status "Ausgegeben"</small>
        </div>

        <!-- Notes -->
        <div class="field">
          <label for="notes" class="font-semibold">Notizen</label>
          <Textarea
            id="notes"
            v-model="formData.notes"
            rows="3"
            class="w-full"
            placeholder="Optional: Zusätzliche Bemerkungen zum Status-Wechsel"
          />
        </div>

        <!-- Actions -->
        <div class="flex gap-2 justify-content-end mt-4">
          <Button
            label="Abbrechen"
            severity="secondary"
            outlined
            @click="handleClose"
            type="button"
          />
          <Button
            label="Status aktualisieren"
            icon="pi pi-check"
            :loading="loading"
            type="submit"
          />
        </div>
      </form>

      <!-- Status Help -->
      <Divider />
      <div class="status-help">
        <h6 class="mb-3"><i class="pi pi-info-circle"></i> Status Hilfe</h6>
        <div class="grid">
          <div class="col-6">
            <div class="help-item mb-3">
              <div class="flex align-items-center gap-2 mb-1">
                <i class="pi pi-plus text-primary"></i>
                <strong>Neu</strong>
              </div>
              <small class="text-600">Neue Bestellung, noch nicht weitergeleitet</small>
            </div>
            <div class="help-item mb-3">
              <div class="flex align-items-center gap-2 mb-1">
                <i class="pi pi-clock text-warning"></i>
                <strong>Bestellt</strong>
              </div>
              <small class="text-600">Artikel wurde bestellt, noch nicht eingegangen</small>
            </div>
          </div>
          <div class="col-6">
            <div class="help-item mb-3">
              <div class="flex align-items-center gap-2 mb-1">
                <i class="pi pi-truck text-info"></i>
                <strong>Eingegangen</strong>
              </div>
              <small class="text-600">Eingegangen, noch nicht ausgegeben</small>
            </div>
            <div class="help-item mb-3">
              <div class="flex align-items-center gap-2 mb-1">
                <i class="pi pi-check-circle text-success"></i>
                <strong>Ausgegeben</strong>
              </div>
              <small class="text-600">An Mitglied ausgegeben</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import Calendar from 'primevue/calendar'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Badge from 'primevue/badge'
import Divider from 'primevue/divider'
import { orderItemsApi } from '@/api/orderItems'
import type { OrderItem, OrderStatus } from '@/types/orders'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  visible: boolean
  item: OrderItem | null
  statusOptions: OrderStatus[]
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const toast = useToast()
const loading = ref(false)
const submitted = ref(false)

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

interface FormData {
  status: number | null
  received_date: Date | null
  delivered_date: Date | null
  notes: string
}

const formData = ref<FormData>({
  status: null,
  received_date: null,
  delivered_date: null,
  notes: ''
})

// Watch for item changes to populate form
watch(() => props.item, (newItem) => {
  if (newItem) {
    formData.value = {
      status: newItem.status,
      received_date: newItem.received_date ? new Date(newItem.received_date) : null,
      delivered_date: newItem.delivered_date ? new Date(newItem.delivered_date) : null,
      notes: newItem.notes || ''
    }
    submitted.value = false
  }
}, { immediate: true })

// Auto-set dates based on status
watch(() => formData.value.status, (newStatusId) => {
  if (!newStatusId) return
  
  const status = props.statusOptions.find(s => s.id === newStatusId)
  if (!status) return
  
  const statusCode = status.code?.toUpperCase() || ''
  
  // Auto-fill received_date for "RECEIVED" status
  if ((statusCode === 'RECEIVED' || statusCode === 'EINGEGANGEN') && !formData.value.received_date) {
    formData.value.received_date = new Date()
  }
  
  // Auto-fill delivered_date and received_date for "DELIVERED" status
  if ((statusCode === 'DELIVERED' || statusCode === 'AUSGEGEBEN')) {
    if (!formData.value.delivered_date) {
      formData.value.delivered_date = new Date()
    }
    if (!formData.value.received_date) {
      formData.value.received_date = new Date()
    }
  }
})

async function handleSubmit() {
  submitted.value = true
  
  if (!formData.value.status) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: 'Bitte wählen Sie einen Status aus',
      life: 3000
    })
    return
  }
  
  if (!props.item) return
  
  loading.value = true
  
  try {
    const updateData: { status: number | null; notes: string; received_date?: string; delivered_date?: string } = {
      status: formData.value.status,
      notes: formData.value.notes
    }
    
    if (formData.value.received_date) {
      updateData.received_date = formData.value.received_date.toISOString()
    }
    
    if (formData.value.delivered_date) {
      updateData.delivered_date = formData.value.delivered_date.toISOString()
    }
    
    await orderItemsApi.updateStatus(props.item.id, formData.value.status, updateData)
    
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: 'Status wurde erfolgreich aktualisiert',
      life: 3000
    })
    
    emit('success')
    handleClose()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: getApiErrorMessage(error, 'Status konnte nicht aktualisiert werden'),
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

function handleClose() {
  isVisible.value = false
  submitted.value = false
}
</script>

<style scoped>
.status-dialog-content {
  padding: 1rem 0;
}

.item-info {
  border: 1px solid var(--primary-200);
}

.status-color-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.status-help {
  padding: 1rem;
  background-color: var(--surface-50);
  border-radius: var(--border-radius);
}

.help-item {
  padding: 0.5rem;
}
</style>
