<template>
  <div class="quick-order-view">
    <Card>
      <template #title>Schnellbestellung</template>
      <template #subtitle>Häufig bestellte Artikel schnell bestellen</template>
      <template #content>
        <form @submit.prevent="handleSubmit">
          <!-- Member Selection -->
          <div class="field">
            <label for="member">Für Mitglied *</label>
            <Dropdown
              id="member"
              v-model="formData.member"
              :options="members"
              optionLabel="full_name"
              optionValue="id"
              placeholder="Mitglied auswählen"
              :filter="true"
              :class="{ 'p-invalid': !formData.member && submitted }"
              class="w-full"
            />
          </div>

          <!-- Common Items Grid -->
          <div class="field">
            <label>Artikel auswählen</label>
            <div class="grid mt-2">
              <div 
                v-for="item in commonItems" 
                :key="item.id"
                class="col-12 md:col-6 lg:col-4"
              >
                <Card class="quick-item-card" :class="{ 'selected': isItemSelected(item.id) }">
                  <template #content>
                    <div class="flex align-items-center gap-2 mb-2">
                      <Checkbox
                        :modelValue="isItemSelected(item.id)"
                        :binary="true"
                        @update:modelValue="(val) => toggleItem(item.id, val)"
                      />
                      <strong>{{ item.name }}</strong>
                    </div>

                    <div v-if="isItemSelected(item.id)">
                      <!-- Size Selection -->
                      <div v-if="item.has_sizes" class="field mb-2">
                        <label class="text-sm">Größe</label>
                        <Dropdown
                          :modelValue="getItemData(item.id)?.size"
                          :options="item.sizes_list"
                          placeholder="Größe wählen"
                          class="w-full"
                          @update:modelValue="(val: string) => updateItemSize(item.id, val)"
                        />
                      </div>

                      <!-- Quantity Selection -->
                      <div class="field mb-0">
                        <label class="text-sm">Menge</label>
                        <InputNumber
                          :modelValue="getItemData(item.id)?.quantity || 1"
                          :min="1"
                          :max="99"
                          class="w-full"
                          @update:modelValue="(val) => updateItemQuantity(item.id, val || 1)"
                        />
                      </div>
                    </div>
                  </template>
                </Card>
              </div>
            </div>
          </div>

          <!-- Notes -->
          <div class="field">
            <label for="notes">Notizen</label>
            <Textarea
              id="notes"
              v-model="formData.notes"
              rows="2"
              class="w-full"
            />
          </div>

          <!-- Actions -->
          <div class="flex gap-2 justify-content-end">
            <Button
              label="Abbrechen"
              severity="secondary"
              outlined
              @click="$emit('cancel')"
              type="button"
            />
            <Button
              label="Zurücksetzen"
              severity="secondary"
              @click="reset"
              type="button"
            />
            <Button
              label="Schnellbestellung erstellen"
              icon="pi pi-shopping-cart"
              :loading="loading"
              :disabled="selectedItems.length === 0"
              type="submit"
            />
          </div>
        </form>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import { useOrdersStore } from '@/stores/orders'
import { useOrderableItemsStore } from '@/stores/orderableItems'
import type { QuickOrderCreate, QuickOrderItem } from '@/types/orders'
import { membersApi, type Member } from '@/api/members'

const emit = defineEmits<{
  success: [orderId: number]
  cancel: []
}>()

const ordersStore = useOrdersStore()
const itemsStore = useOrderableItemsStore()
const toast = useToast()

const loading = ref(false)
const submitted = ref(false)
const members = ref<Member[]>([])

const formData = ref<QuickOrderCreate>({
  member: 0,
  items: [],
  notes: ''
})

const selectedItems = ref<QuickOrderItem[]>([])

// Common items - could be fetched from backend based on frequency
const commonItems = computed(() => {
  return itemsStore.items
    .filter(item => item.is_active)
    .slice(0, 12) // Limit to 12 most common items
})

function isItemSelected(itemId: number): boolean {
  return selectedItems.value.some(i => i.item_id === itemId)
}

function getItemData(itemId: number): QuickOrderItem | undefined {
  return selectedItems.value.find(i => i.item_id === itemId)
}

function toggleItem(itemId: number, selected: boolean) {
  if (selected) {
    selectedItems.value.push({
      item_id: itemId,
      size: '',
      quantity: 1
    })
  } else {
    const index = selectedItems.value.findIndex(i => i.item_id === itemId)
    if (index !== -1) {
      selectedItems.value.splice(index, 1)
    }
  }
}

function updateItemSize(itemId: number, size: string) {
  const item = selectedItems.value.find(i => i.item_id === itemId)
  if (item) {
    item.size = size
  }
}

function updateItemQuantity(itemId: number, quantity: number) {
  const item = selectedItems.value.find(i => i.item_id === itemId)
  if (item) {
    item.quantity = quantity
  }
}

function reset() {
  formData.value = {
    member: 0,
    items: [],
    notes: ''
  }
  selectedItems.value = []
  submitted.value = false
}

async function handleSubmit() {
  submitted.value = true
  
  if (!formData.value.member) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: 'Bitte Mitglied auswählen',
      life: 3000
    })
    return
  }
  
  if (selectedItems.value.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: 'Bitte mindestens einen Artikel auswählen',
      life: 3000
    })
    return
  }
  
  loading.value = true
  
  try {
    formData.value.items = selectedItems.value
    const response = await ordersStore.quickCreateOrder(formData.value)
    
    emit('success', response.id)
    reset()
  } catch (e: any) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: e.message || 'Fehler beim Erstellen der Bestellung',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

async function loadMembers() {
  try {
    const response = await membersApi.list()
    members.value = response.data.results || []
  } catch (e: any) {
    console.error('Failed to load members:', e)
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Mitglieder konnten nicht geladen werden',
      life: 3000
    })
  }
}

onMounted(async () => {
  await itemsStore.fetchItems()
  await loadMembers()
})
</script>

<style scoped>
.quick-order-view {
  max-width: 1200px;
  margin: 0 auto;
}

.quick-item-card {
  height: 100%;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-item-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.quick-item-card.selected {
  border: 2px solid var(--primary-color);
  background-color: var(--primary-50);
}
</style>
