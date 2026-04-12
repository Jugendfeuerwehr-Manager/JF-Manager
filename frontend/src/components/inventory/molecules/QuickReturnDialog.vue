<template>
  <Dialog
    v-model:visible="visible"
    header="Artikel zurückgeben"
    :style="{ width: '500px' }"
    modal
    :closable="!loading"
  >
    <div class="quick-return-form">
      <!-- Step 1: Select Member with loans -->
      <div class="field">
        <label>Von wem wird zurückgegeben? *</label>
        <Dropdown
          v-model="selectedMember"
          :options="membersWithLoans"
          option-label="label"
          option-value="value"
          placeholder="Mitglied auswählen..."
          filter
          filter-placeholder="Name suchen..."
          class="w-full"
          :disabled="!!preselectedMember"
        >
          <template #option="{ option }">
            <div class="member-option">
              <div class="member-info">
                <i class="pi pi-user"></i>
                <span>{{ option.label }}</span>
              </div>
              <Tag :value="`${option.loanCount} Artikel`" severity="info" size="small" />
            </div>
          </template>
        </Dropdown>
      </div>

      <!-- Step 2: Select loaned article -->
      <div v-if="selectedMember" class="field">
        <label>Welcher Artikel wird zurückgegeben? *</label>
        <Dropdown
          v-model="selectedLoan"
          :options="memberLoanedItems"
          option-label="label"
          option-value="value"
          placeholder="Artikel auswählen..."
          class="w-full"
        >
          <template #option="{ option }">
            <div class="loan-option">
              <div class="article-info">
                <span class="article-name">{{ option.label }}</span>
                <Tag v-if="option.category" :value="option.category" severity="secondary" size="small" />
              </div>
              <Tag :value="`${option.quantity} Stück`" severity="secondary" size="small" />
            </div>
          </template>
        </Dropdown>
      </div>

      <!-- Step 3: Return quantity -->
      <div v-if="selectedLoan" class="field">
        <label>Menge zurückgeben *</label>
        <div class="quantity-row">
          <InputNumber
            v-model="quantity"
            :min="1"
            :max="maxQuantity"
            show-buttons
            button-layout="horizontal"
            :input-style="{ width: '60px', textAlign: 'center' }"
          />
          <span class="available-text">von {{ maxQuantity }} ausgeliehen</span>
        </div>
      </div>

      <!-- Step 4: Return destination -->
      <div v-if="selectedLoan" class="field">
        <label>Wohin zurückgeben? *</label>
        <Dropdown
          v-model="targetLocation"
          :options="storageLocationOptions"
          option-label="label"
          option-value="value"
          placeholder="Lagerort auswählen..."
          filter
          class="w-full"
        >
          <template #option="{ option }">
            <div class="location-option">
              <i class="pi pi-box"></i>
              <span>{{ option.label }}</span>
            </div>
          </template>
        </Dropdown>
      </div>

      <!-- Optional Note -->
      <div v-if="selectedLoan" class="field">
        <label>Notiz (optional)</label>
        <InputText v-model="note" placeholder="z.B. Zustand, Beschädigung..." class="w-full" />
      </div>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" text @click="closeDialog" :disabled="loading" />
      <Button
        label="Zurückgeben"
        icon="pi pi-replay"
        :loading="loading"
        @click="submit"
        :disabled="!isValid"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useInventoryStore } from '@/stores/inventory'
import { useToast } from 'primevue/usetoast'

interface Props {
  modelValue: boolean
  preselectedMember?: number
}

const props = withDefaults(defineProps<Props>(), {
  preselectedMember: undefined
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: []
}>()

const inventoryStore = useInventoryStore()
const toast = useToast()

const loading = ref(false)
const selectedMember = ref<number | null>(props.preselectedMember || null)
const selectedLoan = ref<string | null>(null)
const quantity = ref(1)
const targetLocation = ref<number | null>(null)
const note = ref('')

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Members who have loaned items
const membersWithLoans = computed(() => {
  return inventoryStore.memberLoans.map((loan) => ({
    value: loan.location_id,
    label: loan.member_name,
    memberId: loan.member_id,
    loanCount: loan.total_items
  }))
})

// Items loaned by selected member
const memberLoanedItems = computed(() => {
  if (!selectedMember.value) return []

  const memberLoan = inventoryStore.memberLoans.find((l) => l.location_id === selectedMember.value)
  if (!memberLoan) return []

  return memberLoan.items.map((item) => ({
    value: item.variant_id ? `variant:${item.variant_id}:${item.stock_id}` : `item:${item.item_id}:${item.stock_id}`,
    label: item.variant_display || item.item_name || 'Unbekannter Artikel',
    category: item.category_name,
    quantity: item.quantity,
    stockId: item.stock_id
  }))
})

const selectedLoanInfo = computed(() => {
  if (!selectedLoan.value) return null
  return memberLoanedItems.value.find((l) => l.value === selectedLoan.value)
})

const maxQuantity = computed(() => {
  return selectedLoanInfo.value?.quantity || 0
})

// Storage locations for return destination
const storageLocationOptions = computed(() => {
  return inventoryStore.storageLocations.map((l) => ({
    value: l.id,
    label: l.full_path || l.name
  }))
})

const isValid = computed(() => {
  return (
    selectedMember.value &&
    selectedLoan.value &&
    quantity.value > 0 &&
    quantity.value <= maxQuantity.value &&
    targetLocation.value
  )
})

// Reset when dialog opens
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      selectedMember.value = props.preselectedMember || null
      selectedLoan.value = null
      quantity.value = 1
      targetLocation.value = inventoryStore.storageLocations[0]?.id || null
      note.value = ''
    }
  }
)

// Reset loan selection when member changes
watch(selectedMember, () => {
  selectedLoan.value = null
  quantity.value = 1
})

// Set quantity to max when loan is selected
watch(selectedLoan, () => {
  quantity.value = maxQuantity.value || 1
})

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!isValid.value || !selectedLoan.value || !selectedMember.value || !targetLocation.value) return

  loading.value = true
  try {
    const parts = selectedLoan.value.split(':')
    const type = parts[0] || 'item'
    const id = parseInt(parts[1] || '0')

    await inventoryStore.createTransaction({
      transaction_type: 'RETURN',
      item: type === 'item' ? id : null,
      item_variant: type === 'variant' ? id : null,
      source: selectedMember.value,
      target: targetLocation.value,
      quantity: quantity.value,
      note: note.value
    })

    toast.add({
      severity: 'success',
      summary: 'Zurückgegeben',
      detail: `${quantity.value}x ${selectedLoanInfo.value?.label} erfolgreich zurückgegeben.`,
      life: 3000
    })

    emit('success')
    closeDialog()
  } catch (err: unknown) {
    const errorMessage = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Ein Fehler ist aufgetreten'
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: errorMessage,
      life: 5000
    })
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.quick-return-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-color);
}

.member-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.member-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loan-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0.25rem 0;
}

.article-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.article-name {
  font-weight: 500;
}

.location-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quantity-row {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.available-text {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
}

.w-full {
  width: 100%;
}
</style>
