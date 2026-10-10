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

      <!-- Step 2: Part quantities per issued article (UX-05.1) -->
      <fieldset v-if="selectedMember" class="field return-lines">
        <legend>Was wird zurückgegeben? *</legend>
        <p v-if="!memberLoanedItems.length" class="available-text">An dieses Mitglied ist nichts ausgegeben.</p>
        <div v-for="line in memberLoanedItems" :key="line.key" class="return-line">
          <div class="article-info">
            <span :id="`return-label-${line.key}`" class="article-name">{{ line.label }}</span>
            <span class="available-text">{{ line.quantity }} ausgegeben</span>
          </div>
          <div class="quantity-row">
            <InputNumber
              v-model="quantities[line.key]"
              :min="0"
              :max="line.quantity"
              show-buttons
              button-layout="horizontal"
              :input-style="{ width: '60px', textAlign: 'center' }"
              :aria-labelledby="`return-label-${line.key}`"
            />
            <Button label="Alles" size="small" text :aria-label="`${line.label}: alles zurückgeben`" @click="quantities[line.key] = line.quantity" />
          </div>
        </div>
        <p v-if="memberLoanedItems.length" class="available-text" role="status">{{ summary }}</p>
      </fieldset>

      <!-- Step 4: Return destination -->
      <div v-if="returnLines.length" class="field">
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
      <div v-if="returnLines.length" class="field">
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
import { getApiErrorMessage } from '@/utils/apiError'

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
const memberLoan = computed(() => inventoryStore.memberLoans.find((l) => l.location_id === selectedMember.value) ?? null)

const memberLoanedItems = computed(() => {
  if (!memberLoan.value) return []
  return memberLoan.value.items.map((item) => ({
    key: item.variant_id ? `variant:${item.variant_id}` : `item:${item.item_id}`,
    itemId: item.variant_id ? null : item.item_id,
    variantId: item.variant_id,
    label: item.variant_display || item.item_name || 'Unbekannter Artikel',
    quantity: item.quantity,
  }))
})

// Quantity to take back per article; 0 keeps it with the member.
const quantities = ref<Record<string, number>>({})

const returnLines = computed(() =>
  memberLoanedItems.value
    .map((line) => ({ line, quantity: quantities.value[line.key] ?? 0 }))
    .filter(({ line, quantity }) => quantity > 0 && quantity <= line.quantity),
)

const summary = computed(() => {
  const pieces = returnLines.value.reduce((sum, { quantity }) => sum + quantity, 0)
  if (!pieces) return 'Noch nichts ausgewählt.'
  const articles = returnLines.value.length
  return `${pieces} Stück aus ${articles} ${articles === 1 ? 'Artikel' : 'Artikeln'} werden zurückgenommen.`
})

// Storage locations for return destination
const storageLocationOptions = computed(() => {
  return inventoryStore.storageLocations.map((l) => ({
    value: l.id,
    label: l.full_path || l.name
  }))
})

const isValid = computed(() => Boolean(selectedMember.value && memberLoan.value && returnLines.value.length && targetLocation.value))

// Reset when dialog opens
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal) {
      selectedMember.value = props.preselectedMember || null
      quantities.value = {}
      targetLocation.value = inventoryStore.storageLocations[0]?.id || null
      note.value = ''
    }
  }
)

// Start with nothing selected for another member
watch(selectedMember, () => {
  quantities.value = {}
})

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!isValid.value || !targetLocation.value) return

  if (!memberLoan.value) return
  loading.value = true
  try {
    const result = await inventoryStore.batchReturn({
      member: memberLoan.value.member_id,
      items: returnLines.value.map(({ line, quantity }) => ({
        item: line.itemId,
        item_variant: line.variantId,
        quantity,
        target: targetLocation.value as number,
      })),
      note: note.value,
    })

    toast.add({
      severity: 'success',
      summary: 'Zurückgenommen',
      detail: `${result.returned_quantity} Stück von ${memberLoan.value.member_name} zurückgenommen.`,
      life: 3000
    })

    emit('success')
    closeDialog()
  } catch (err: unknown) {
    const errorMessage = getApiErrorMessage(err, 'Die Rücknahme wurde nicht gebucht.')
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

.return-lines {
  border: 0;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.return-lines legend {
  font-weight: 600;
  margin-bottom: var(--jf-space-1);
}

.return-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-2);
  padding: var(--jf-space-2) 0;
  border-bottom: 1px solid var(--jf-color-border);
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
