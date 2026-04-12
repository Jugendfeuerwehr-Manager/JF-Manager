<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import type { SpecialTaskTypeCreate, SpecialTaskTypeUpdate, SpecialTaskType } from '@/types/qualifications'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  typeId?: number
  initialData?: SpecialTaskType
}

const props = defineProps<Props>()

const emit = defineEmits<{
  success: [typeId: number]
  cancel: []
}>()

const qualificationsStore = useQualificationsStore()

// Form state
const formData = ref<SpecialTaskTypeCreate>({
  name: '',
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
      description: props.initialData.description || ''
    }
  } else if (props.typeId) {
    // Fetch single type
    await qualificationsStore.fetchSpecialTaskTypes()
    const type = qualificationsStore.specialTaskTypes.find(t => t.id === props.typeId)
    if (type) {
      formData.value = {
        name: type.name,
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
      const updateData: SpecialTaskTypeUpdate = { ...formData.value }
      await qualificationsStore.updateSpecialTaskType(id, updateData)
      emit('success', id)
    } else {
      const newType = await qualificationsStore.createSpecialTaskType(formData.value)
      emit('success', newType.id)
    }
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Fehler beim Speichern des Aufgabentyps')
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<template>

      <Message v-if="error" severity="error" :closable="false" class="mb-4">
        {{ error }}
      </Message>

      <form @submit.prevent="handleSubmit" class="flex flex-column gap-4">
        <!-- Name -->
        <div class="flex flex-column gap-2">
          <label for="name" class="font-semibold">
            Name *
          </label>
          <InputText
            id="name"
            v-model="formData.name"
            placeholder="z.B. Jugendwart, Kassenwart, Gerätewart"
            :disabled="loading"
            class="w-full"
            :class="{ 'p-invalid': !formData.name.trim() && formData.name.length > 0 }"
          />
          <small class="text-gray-600">
            Bezeichnung der Sonderaufgabe (wird in der Übersicht angezeigt)
          </small>
        </div>

        <!-- Description -->
        <div class="flex flex-column gap-2">
          <label for="description" class="font-semibold">
            Beschreibung
          </label>
          <Textarea
            id="description"
            v-model="formData.description"
            rows="4"
            placeholder="Beschreiben Sie die Aufgaben und Verantwortlichkeiten..."
            :disabled="loading"
            class="w-full"
            autoResize
          />
          <small class="text-gray-600">
            Optionale ausführliche Beschreibung der Aufgabe und ihrer Verantwortlichkeiten
          </small>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2 justify-end mt-4 pt-4 border-t">
          <Button
            label="Abbrechen"
            icon="pi pi-times"
            severity="secondary"
            @click="handleCancel"
            :disabled="loading"
          />
          <Button
            type="submit"
            :label="isEditMode ? 'Aktualisieren' : 'Erstellen'"
            :icon="isEditMode ? 'pi pi-check' : 'pi pi-plus'"
            :loading="loading"
            :disabled="!isFormValid"
          />
        </div>
      </form>
</template>
