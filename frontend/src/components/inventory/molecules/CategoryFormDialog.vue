<template>
  <Dialog
    v-model:visible="visible"
    :header="isEdit ? 'Kategorie bearbeiten' : 'Neue Kategorie'"
    :style="{ width: '400px' }"
    modal
    :closable="!loading"
  >
    <div class="category-form">
      <div class="field">
        <label for="name">Name *</label>
        <InputText id="name" v-model="form.name" class="w-full" placeholder="z.B. Bekleidung, Material" />
      </div>
    </div>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" text @click="closeDialog" :disabled="loading" />
      <Button
        :label="isEdit ? 'Speichern' : 'Erstellen'"
        icon="pi pi-check"
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
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { useInventoryStore } from '@/stores/inventory'
import { useToast } from 'primevue/usetoast'
import type { Category, CategoryCreate } from '@/types/inventory'

interface Props {
  modelValue: boolean
  category?: Category | null
}

const props = withDefaults(defineProps<Props>(), {
  category: null
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: [category: Category]
}>()

const inventoryStore = useInventoryStore()
const toast = useToast()

const loading = ref(false)

const form = ref<CategoryCreate>({
  name: '',
  schema: null
})

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const isEdit = computed(() => !!props.category)

const isValid = computed(() => !!form.value.name)

// Initialize form from props
watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal && props.category) {
      form.value = {
        name: props.category.name,
        schema: props.category.schema
      }
    } else if (newVal) {
      form.value = {
        name: '',
        schema: null
      }
    }
  },
  { immediate: true }
)

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!isValid.value) return

  loading.value = true
  try {
    let result: Category

    if (isEdit.value && props.category) {
      result = await inventoryStore.updateCategory(props.category.id, form.value)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Kategorie wurde aktualisiert',
        life: 3000
      })
    } else {
      result = await inventoryStore.createCategory(form.value)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Kategorie wurde erstellt',
        life: 3000
      })
    }

    emit('success', result)
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
.category-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field label {
  font-weight: 600;
  font-size: 0.875rem;
}

.w-full {
  width: 100%;
}
</style>
