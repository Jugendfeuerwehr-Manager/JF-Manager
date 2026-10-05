<template>
  <Dialog
    v-model:visible="visible"
    :header="`Mitglied löschen: ${memberName}`"
    :modal="true"
    :closable="!loading"
    :close-on-escape="!loading"
    style="max-width: 560px; width: 95vw"
  >
    <div class="deletion-dialog-content">
      <Message severity="warn" :closable="false" class="mb-3">
        <strong>{{ memberName }}</strong> hat
        <strong>{{ transactionCount }} Transaktion{{ transactionCount !== 1 ? 'en' : '' }}</strong>
        im Lager, die mit diesem Mitglied verknüpft sind.<br />
        Bitte buchen Sie verbleibende Bestände zuerst zurück. Wählen Sie dann, ob der Name
        des persönlichen Lagerorts erhalten bleibt.
      </Message>

      <div class="strategy-options">
        <!-- Option 1: Store name -->
        <div
          class="strategy-card"
          :class="{ selected: selectedStrategy === 'unlink' }"
          @click="selectedStrategy = 'unlink'"
        >
          <div class="strategy-header">
            <RadioButton
              v-model="selectedStrategy"
              input-id="strategy-unlink"
              value="unlink"
            />
            <label for="strategy-unlink" class="strategy-title">
              <i class="pi pi-user-minus mr-2" />
              Lagerortnamen behalten
            </label>
          </div>
          <p class="strategy-description">
            Der Name des persönlichen Lagerorts bleibt in der Buchungshistorie sichtbar.
            Die Verknüpfung zum Mitglied wird aufgehoben.
          </p>
          <p class="strategy-note strategy-note--warn">
            <i class="pi pi-exclamation-triangle mr-1" />
            Hinweis: Ein personenbezogener Lagerortname bleibt in der Datenbank.
          </p>
        </div>

        <!-- Option 2: Anonymize -->
        <div
          class="strategy-card"
          :class="{ selected: selectedStrategy === 'anonymize' }"
          @click="selectedStrategy = 'anonymize'"
        >
          <div class="strategy-header">
            <RadioButton
              v-model="selectedStrategy"
              input-id="strategy-anonymize"
              value="anonymize"
            />
            <label for="strategy-anonymize" class="strategy-title">
              <i class="pi pi-shield mr-2" />
              Lagerortnamen anonymisieren
            </label>
          </div>
          <p class="strategy-description">
            Der persönliche Lagerort erhält einen neutralen Namen. Buchungen und Bestände
            bleiben erhalten.
          </p>
          <p class="strategy-note strategy-note--success">
            <i class="pi pi-check-circle mr-1" />
            Empfohlen, wenn der Lagerortname personenbezogen ist.
          </p>
        </div>

      </div>
    </div>

    <template #footer>
      <Button
        label="Abbrechen"
        severity="secondary"
        outlined
        :disabled="loading"
        @click="visible = false"
      />
      <Button
        :label="confirmLabel"
        severity="primary"
        :loading="loading"
        :disabled="!selectedStrategy"
        @click="confirm"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import RadioButton from 'primevue/radiobutton'
import Message from 'primevue/message'
import type { MemberDeletionStrategy } from '@/types/inventory'

interface Props {
  memberName: string
  transactionCount: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), { loading: false })
void props

const emit = defineEmits<{
  confirm: [strategy: MemberDeletionStrategy]
  cancel: []
}>()

const visible = defineModel<boolean>({ required: true })
const selectedStrategy = ref<MemberDeletionStrategy | null>(null)

const confirmLabel = computed(() => {
  switch (selectedStrategy.value) {
    case 'unlink':
      return 'Lagerort behalten & löschen'
    case 'anonymize':
      return 'Anonymisieren & löschen'
    default:
      return 'Strategie wählen'
  }
})

function confirm() {
  if (!selectedStrategy.value) return
  emit('confirm', selectedStrategy.value)
}

// Reset selection when dialog opens/closes
watch(visible, (val) => {
  if (!val) {
    selectedStrategy.value = null
  }
})
</script>

<style scoped>
.deletion-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.strategy-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.strategy-card {
  border: 2px solid var(--p-surface-border, #e2e8f0);
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.strategy-card:hover {
  border-color: var(--p-primary-color, #6366f1);
  background-color: var(--p-primary-50, #eef2ff);
}

.strategy-card.selected {
  border-color: var(--p-primary-color, #6366f1);
  background-color: var(--p-primary-50, #eef2ff);
}

.strategy-card--danger:hover,
.strategy-card--danger.selected {
  border-color: var(--p-red-500, #ef4444);
  background-color: var(--p-red-50, #fef2f2);
}

.strategy-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.strategy-title {
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.strategy-description {
  margin: 0 0 0.5rem 1.75rem;
  color: var(--p-text-muted-color, #6b7280);
  font-size: 0.875rem;
}

.strategy-note {
  margin: 0 0 0 1.75rem;
  font-size: 0.8rem;
  display: flex;
  align-items: flex-start;
  gap: 0.25rem;
}

.strategy-note--warn {
  color: var(--p-orange-700, #c2410c);
}

.strategy-note--success {
  color: var(--p-green-700, #15803d);
}

.strategy-note--danger {
  color: var(--p-red-700, #b91c1c);
}

.mb-3 {
  margin-bottom: 0.75rem;
}

.mr-1 {
  margin-right: 0.25rem;
}

.mr-2 {
  margin-right: 0.5rem;
}
</style>
