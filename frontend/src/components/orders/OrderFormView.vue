<template>
  <div class="order-form">
    <Card>
      <template #title>
        <div class="flex align-items-center gap-2">
          <Button 
            icon="pi pi-arrow-left" 
            severity="secondary"
            text
            @click="handleBack"
            v-tooltip.top="'Zurück'"
          />
          <span>{{ isEdit ? 'Bestellung bearbeiten' : 'Neue Bestellung' }}</span>
        </div>
      </template>
      <template #content>
        <form @submit.prevent="handleSubmit">
          <!-- Member Selection -->
          <div class="field">
            <label for="member">Mitglied *</label>
            <Dropdown
              id="member"
              v-model="formData.member"
              :options="members"
              optionLabel="full_name"
              optionValue="id"
              placeholder="Mitglied auswählen"
              :filter="true"
              :class="{ 'p-invalid': errors.member }"
              class="w-full"
            />
            <small v-if="errors.member" class="p-error">{{ errors.member }}</small>
          </div>

          <!-- Notes -->
          <div class="field">
            <label for="notes">Notizen</label>
            <Textarea
              id="notes"
              v-model="formData.notes"
              rows="3"
              class="w-full"
            />
          </div>

          <!-- Items -->
          <div class="field">
            

            <div v-if="formData.items.length === 0" class="text-center text-500 p-4 border-1 border-round">
              Keine Artikel hinzugefügt
            </div>

            <div v-for="(item, index) in formData.items" :key="index" class="mb-3 p-3 surface-100 border-round">
              <div class="grid">
                <div class="col-12 md:col-5">
                  <label :for="`item-${index}`">Artikel</label>
                  <Dropdown
                    :id="`item-${index}`"
                    v-model="item.item"
                    :options="orderableItems"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Artikel wählen"
                    :filter="true"
                    :class="{ 'p-invalid': errors[`items.${index}.item`] }"
                    class="w-full"
                    @change="onItemChange(index)"
                  />
                  <small v-if="errors[`items.${index}.item`]" class="p-error">
                    {{ errors[`items.${index}.item`] }}
                  </small>
                </div>

                <div class="col-12 md:col-3">
                  <label :for="`size-${index}`">Größe</label>
                  <Dropdown
                    v-if="getItemSizes(item.item).length > 0"
                    :id="`size-${index}`"
                    v-model="item.size"
                    :options="getItemSizes(item.item)"
                    placeholder="Größe"
                    class="w-full"
                  />
                  <InputText
                    v-else
                    :id="`size-${index}`"
                    v-model="item.size"
                    placeholder="Größe (optional)"
                    class="w-full"
                  />
                </div>

                <div class="col-12 md:col-3">
                  <label :for="`quantity-${index}`">Menge</label>
                  <InputNumber
                    :id="`quantity-${index}`"
                    v-model="item.quantity"
                    :min="1"
                    :max="999"
                    :class="{ 'p-invalid': errors[`items.${index}.quantity`] }"
                    class="w-full"
                  />
                  <small v-if="errors[`items.${index}.quantity`]" class="p-error">
                    {{ errors[`items.${index}.quantity`] }}
                  </small>
                </div>

                <div class="col-12 md:col-1 flex align-items-end">
                  <Button
                    icon="pi pi-trash"
                    severity="danger"
                    text
                    @click="removeItem(index)"
                    type="button"
                  />
                </div>
              </div>
            </div>
          </div>
          <div class="flex justify-content-between align-items-center mb-2">
              <label>Artikel *</label>
              <Button
                label="Artikel hinzufügen"
                icon="pi pi-plus"
                size="small"
                @click="addItem"
                type="button"
              />
            </div>
            <hr><br>          <!-- Actions -->
          <div class="flexgap-2 justify-content-end">
            <Button
              label="Abbrechen"
              severity="secondary"
              @click="$emit('cancel')"
              type="button"
            />
            <Button
              label="Speichern"
              icon="pi pi-check"
              :loading="loading"
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
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import { useOrdersStore } from '@/stores/orders'
import { useOrderableItemsStore } from '@/stores/orderableItems'
import { useMembersStore } from '@/stores/members'
import type { OrderCreate } from '@/types/orders'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  orderId?: number
  initialMemberId?: number
}

const props = defineProps<Props>()
const emit = defineEmits<{
  cancel: []
  success: [orderId: number]
}>()

const router = useRouter()
const ordersStore = useOrdersStore()
const itemsStore = useOrderableItemsStore()
const membersStore = useMembersStore()
const toast = useToast()

const loading = ref(false)
const errors = ref<Record<string, string>>({})
const members = computed(() => membersStore.members)

const formData = ref<OrderCreate>({
  member: props.initialMemberId || 0,
  notes: '',
  items: []
})

const isEdit = computed(() => !!props.orderId)
const orderableItems = computed(() => itemsStore.items.filter(i => i.is_active))

function getItemSizes(itemId: number): string[] {
  const item = itemsStore.items.find(i => i.id === itemId)
  return item?.sizes_list || []
}

function onItemChange(index: number) {
  // Clear size when item changes
  const item = formData.value.items[index]
  if (item) {
    item.size = ''
  }
}

function addItem() {
  formData.value.items.push({
    item: 0,
    size: '',
    quantity: 1
  })
}

function removeItem(index: number) {
  formData.value.items.splice(index, 1)
}

function validate(): boolean {
  errors.value = {}
  
  if (!formData.value.member) {
    errors.value.member = 'Bitte Mitglied auswählen'
  }
  
  if (formData.value.items.length === 0) {
    toast.add({
      severity: 'warn',
      summary: 'Warnung',
      detail: 'Bitte mindestens einen Artikel hinzufügen',
      life: 3000
    })
    return false
  }
  
  formData.value.items.forEach((item, index) => {
    if (!item.item) {
      errors.value[`items.${index}.item`] = 'Artikel wählen'
    }
    if (item.quantity < 1) {
      errors.value[`items.${index}.quantity`] = 'Menge min. 1'
    }
  })
  
  return Object.keys(errors.value).length === 0
}

function handleBack() {
  if (isEdit.value && props.orderId) {
    router.push({ name: 'order-detail', params: { id: props.orderId } })
  } else {
    router.push({ name: 'orders' })
  }
}

async function handleSubmit() {
  if (!validate()) return
  
  loading.value = true
  
  try {
    if (isEdit.value) {
      // For edit, we'd need to update items separately
      // This is simplified - in reality you'd need more complex logic
      await ordersStore.updateOrder(props.orderId!, {
        member: formData.value.member,
        notes: formData.value.notes
      })
    } else {
      const response = await ordersStore.createOrder(formData.value)
      emit('success', response.id)
    }
    
    toast.add({
      severity: 'success',
      summary: 'Erfolg',
      detail: isEdit.value ? 'Bestellung aktualisiert' : 'Bestellung erstellt',
      life: 3000
    })
  } catch (e) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: getApiErrorMessage(e, 'Fehler beim Speichern'),
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

async function loadMembers() {
  try {
    await membersStore.fetchMembers({ limit: 1000 })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Mitglieder konnten nicht geladen werden',
      life: 3000
    })
  }
}

async function loadOrderForEdit() {
  if (!props.orderId) return
  
  try {
    await ordersStore.fetchOrder(props.orderId)
    const order = ordersStore.currentOrder
    if (order) {
      formData.value = {
        member: order.member,
        notes: order.notes,
        items: order.items.map(item => ({
          item: item.item,
          size: item.size,
          quantity: item.quantity
        }))
      }
    }
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Bestellung konnte nicht geladen werden',
      life: 3000
    })
  }
}

onMounted(async () => {
  await itemsStore.fetchItems()
  await loadMembers()
  if (props.orderId) {
    await loadOrderForEdit()
  }
})
</script>

<style scoped>
.order-form {
  max-width: 900px;
  margin: 0 auto;
}
</style>
