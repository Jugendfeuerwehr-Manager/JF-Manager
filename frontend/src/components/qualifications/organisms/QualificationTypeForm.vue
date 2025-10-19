<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import type { QualificationTypeCreate, QualificationTypeUpdate, QualificationType } from '@/types/qualifications'
import Card from 'primevue/card'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import InputSwitch from 'primevue/inputswitch'
import Button from 'primevue/button'
import Message from 'primevue/message'

interface Props {
  typeId?: number
  initialData?: QualificationType
}

const props = defineProps<Props>()

const emit = defineEmits<{
  success: [typeId: number]
  cancel: []
}>()

const qualificationsStore = useQualificationsStore()

// Form state
const formData = ref<QualificationTypeCreate>({
  name: '',
  expires: false,
  validity_period: null,
  description: ''
})

const loading = ref(false)
const error = ref<string | null>(null)
const isEditMode = computed(() => !!props.typeId || !!props.initialData)

// Load initial data if editing
onMounted(async () => {
  if (props.initialData) {
    formData.value = {
      name: props.initialData.name,
      expires: props.initialData.expires,
      validity_period: props.initialData.validity_period,
      description: props.initialData.description || ''
    }
  } else if (props.typeId) {
    // Fetch single type
    await qualificationsStore.fetchQualificationTypes()
    const type = qualificationsStore.qualificationTypes.find(t => t.id === props.typeId)
    if (type) {
      formData.value = {
        name: type.name,
        expires: type.expires,
        validity_period: type.validity_period,
        description: type.description || ''
      }
    }
  }
})

// Form validation
const isFormValid = computed(() => {
  return formData.value.name.trim().length > 0
})

// Submit handler
const handleSubmit = async () => {
  if (!isFormValid.value) {
    error.value = 'Bitte geben Sie einen Namen ein.'
    return
  }

  loading.value = true
  error.value = null

  try {
    if (isEditMode.value && (props.typeId || props.initialData?.id)) {
      const id = props.typeId || props.initialData!.id
      const updateData: QualificationTypeUpdate = { ...formData.value }
      await qualificationsStore.updateQualificationType(id, updateData)
      emit('success', id)
    } else {
      const newType = await qualificationsStore.createQualificationType(formData.value)
      emit('success', newType.id)
    }
  } catch (err: any) {
    error.value = err.message || 'Fehler beim Speichern des Qualifikationstyps'
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<template>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <form @submit.prevent="handleSubmit" class="flex flex-column gap-4">
        <!-- Name -->
        <div class="flex flex-column gap-2">
          <label for="name" class="font-semibold">Name *</label>
          <InputText
            id="name"
            v-model="formData.name"
            placeholder="z.B. Truppmann"
            :disabled="loading"
            class="w-full"
          />
        </div>

        <!-- Expires -->
        <div class="flex flex-column gap-2">
          <div class="flex items-center gap-3">
            <InputSwitch
              id="expires"
              v-model="formData.expires"
              :disabled="loading"
            />
            <label for="expires" class="font-semibold cursor-pointer">
              Qualifikation läuft ab
            </label>
          </div>
          <small class="text-gray-600">
            Aktivieren, wenn diese Qualifikation nach einer bestimmten Zeit abläuft
          </small>
        </div>

        <!-- Validity Period -->
        <div v-if="formData.expires" class="flex flex-column gap-2">
          <label for="validity_period" class="font-semibold">Gültigkeitsdauer (Monate)</label>
          <InputNumber
            id="validity_period"
            v-model="formData.validity_period"
            placeholder="z.B. 24 für 2 Jahre"
            :disabled="loading"
            :min="1"
            :max="120"
            class="w-full"
            suffix=" Monate"
          />
          <small class="text-gray-600">
            Standardgültigkeitsdauer für diese Qualifikation
          </small>
        </div>

        <!-- Description -->
        <div class="flex flex-column gap-2">
          <label for="description" class="font-semibold">Beschreibung</label>
          <Textarea
            id="description"
            v-model="formData.description"
            rows="3"
            placeholder="Optionale Beschreibung"
            :disabled="loading"
            class="w-full"
          />
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2 justify-end mt-4">
          <Button
            label="Abbrechen"
            severity="secondary"
            @click="handleCancel"
            :disabled="loading"
          />
          <Button
            type="submit"
            :label="isEditMode ? 'Aktualisieren' : 'Erstellen'"
            :loading="loading"
            :disabled="!isFormValid"
          />
        </div>
      </form>
</template>
