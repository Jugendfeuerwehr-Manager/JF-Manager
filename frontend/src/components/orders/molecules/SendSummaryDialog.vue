<template>
  <Dialog
    :visible="visible"
    header="Bestellübersicht an Gerätewart senden"
    :modal="true"
    :style="{ width: '600px' }"
    @update:visible="$emit('update:visible', $event)"
  >
    <div class="flex flex-column gap-4">
      <Message severity="info" :closable="false">
        <p class="m-0">
          <strong>Alle Bestellungen mit Status "Neu"</strong> werden gesammelt und per E-Mail 
          an den Gerätewart gesendet. Nach erfolgreichem Versand wird der Status automatisch 
          auf "Bestellt bei Gerätewart" geändert.
        </p>
      </Message>

      <div v-if="newOrdersCount > 0" class="field">
        <div class="surface-100 border-round p-3">
          <div class="flex align-items-center gap-2 mb-2">
            <i class="pi pi-info-circle text-primary"></i>
            <strong>{{ newOrdersCount }} neue {{ newOrdersCount === 1 ? 'Bestellung' : 'Bestellungen' }}</strong>
          </div>
          <div class="text-sm text-600">
            Diese Bestellungen werden in der Übersicht versendet.
          </div>
        </div>
      </div>

      <div v-else class="field">
        <Message severity="warn" :closable="false">
          Keine neuen Bestellungen gefunden.
        </Message>
      </div>

      <div class="field">
        <label for="email" class="block mb-2 font-semibold">
          E-Mail-Adresse des Gerätewarts *
        </label>
        <InputText
          id="email"
          v-model="email"
          type="email"
          placeholder="geraetewart@feuerwehr.de"
          class="w-full"
          :disabled="sending || newOrdersCount === 0"
          :class="{ 'p-invalid': !isValidEmail && email.length > 0 }"
        />
        <small v-if="!isValidEmail && email.length > 0" class="p-error">
          Bitte geben Sie eine gültige E-Mail-Adresse ein
        </small>
      </div>

      <div class="field">
        <label for="notes" class="block mb-2 font-semibold">
          Zusätzliche Notizen (optional)
        </label>
        <Textarea
          id="notes"
          v-model="additionalNotes"
          rows="3"
          placeholder="Zusätzliche Informationen für den Gerätewart..."
          class="w-full"
          :disabled="sending || newOrdersCount === 0"
        />
      </div>

      <div class="field">
        <div class="flex flex-column gap-2">
          <div class="flex align-items-center">
            <Checkbox
              id="include-notes"
              v-model="includeNotes"
              :binary="true"
              :disabled="sending || newOrdersCount === 0"
            />
            <label for="include-notes" class="ml-2">Notizen aus Bestellungen einbeziehen</label>
          </div>
          <div class="flex align-items-center">
            <Checkbox
              id="group-by-category"
              v-model="groupByCategory"
              :binary="true"
              :disabled="sending || newOrdersCount === 0"
            />
            <label for="group-by-category" class="ml-2">Nach Kategorien gruppieren</label>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <Button
        label="Abbrechen"
        icon="pi pi-times"
        @click="handleCancel"
        severity="secondary"
        :disabled="sending"
      />
      <Button
        label="Übersicht senden"
        icon="pi pi-send"
        @click="handleSend"
        :loading="sending"
        :disabled="!canSend"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import { useOrdersStore } from '@/stores/orders'
import { useSettingsStore } from '@/stores/settings'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  visible: boolean
  newOrdersCount: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  success: []
  error: [error: unknown]
}>()

const ordersStore = useOrdersStore()
const settingsStore = useSettingsStore()
const toast = useToast()

const email = ref('')
const additionalNotes = ref('')
const includeNotes = ref(true)
const groupByCategory = ref(true)
const sending = ref(false)

const isValidEmail = computed(() => {
  if (email.value.length === 0) return true
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email.value)
})

const canSend = computed(() => {
  return props.newOrdersCount > 0 && email.value.length > 0 && isValidEmail.value && !sending.value
})

// Lifecycle - Load settings on mount
onMounted(async () => {
  if (!settingsStore.order) {
    try {
      await settingsStore.fetchAllSettings()
    } catch {
    }
  }
})

// Watch for settings changes to update email
watch(() => settingsStore.equipmentManagerEmail, (newEmail) => {
  if (newEmail && !email.value) {
    email.value = newEmail
  }
}, { immediate: true })

// Reset when dialog opens
watch(() => props.visible, (isVisible) => {
  if (isVisible) {
    // Set email from settings if not already set
    if (!email.value && settingsStore.equipmentManagerEmail) {
      email.value = settingsStore.equipmentManagerEmail
    }
  }
})

function handleCancel() {
  emit('update:visible', false)
  // Reset after animation
  setTimeout(() => {
    email.value = settingsStore.equipmentManagerEmail
    additionalNotes.value = ''
    includeNotes.value = true
    groupByCategory.value = true
  }, 300)
}

async function handleSend() {
  if (!canSend.value) return
  
  sending.value = true
  
  try {
    await ordersStore.sendSummary({
      recipient_email: email.value,
      include_notes: includeNotes.value,
      group_by_category: groupByCategory.value,
      additional_notes: additionalNotes.value
    })
    
    toast.add({
      severity: 'success',
      summary: 'Erfolgreich versendet',
      detail: `Bestellübersicht wurde an ${email.value} gesendet`,
      life: 5000
    })
    
    emit('success')
    emit('update:visible', false)
    
    // Reset form
    setTimeout(() => {
      email.value = settingsStore.equipmentManagerEmail
      additionalNotes.value = ''
      includeNotes.value = true
      groupByCategory.value = true
    }, 300)
  } catch (error) {
    const errorMessage = getApiErrorMessage(error, 'Fehler beim Versenden der Bestellübersicht')
    
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: errorMessage,
      life: 5000
    })
    
    emit('error', error)
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.p-dialog :deep(.p-dialog-header) {
  background: var(--primary-color);
  color: white;
}
</style>
