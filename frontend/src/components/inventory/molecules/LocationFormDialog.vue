<template>
  <Dialog
    v-model:visible="visible"
    :header="isEdit ? 'Lagerort bearbeiten' : 'Neuer Lagerort'"
    :style="{ width: '500px' }"
    modal
    :closable="!loading"
  >
    <div class="location-form">
      <div class="field">
        <label for="name">Name *</label>
        <InputText id="name" v-model="form.name" class="w-full" placeholder="z.B. Schrank 1, Raum A" />
      </div>

      <div class="field">
        <label for="parent">Übergeordneter Lagerort</label>
        <Dropdown
          id="parent"
          v-model="form.parent"
          :options="parentOptions"
          option-label="label"
          option-value="value"
          placeholder="Keiner (Hauptlagerort)"
          show-clear
          class="w-full"
        />
      </div>

      <Divider />

      <div class="field">
        <div class="flex align-items-center gap-2">
          <Checkbox v-model="form.is_member" input-id="isMember" binary />
          <label for="isMember">Mitglieder-Lagerort (für Ausleihen)</label>
        </div>
        <small class="text-muted">
          Aktivieren Sie dies, um diesen Lagerort einem Mitglied zuzuordnen. Artikel an diesem Ort gelten als ausgeliehen.
        </small>
      </div>

      <div v-if="form.is_member" class="field">
        <label for="member">Mitglied *</label>
        <Dropdown
          id="member"
          v-model="form.member"
          :options="memberOptions"
          option-label="label"
          option-value="value"
          placeholder="Mitglied auswählen"
          filter
          class="w-full"
        />
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
import Dropdown from 'primevue/dropdown'
import Checkbox from 'primevue/checkbox'
import Divider from 'primevue/divider'
import Button from 'primevue/button'
import { useInventoryStore } from '@/stores/inventory'
import { useMembersStore } from '@/stores/members'
import { useToast } from 'primevue/usetoast'
import type { StorageLocation, StorageLocationCreate, StorageLocationUpdate } from '@/types/inventory'

interface Props {
  modelValue: boolean
  location?: StorageLocation | null
  defaultParent?: number | null
}

const props = withDefaults(defineProps<Props>(), {
  location: null,
  defaultParent: null
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: [location: StorageLocation]
}>()

const inventoryStore = useInventoryStore()
const membersStore = useMembersStore()
const toast = useToast()

const loading = ref(false)

const form = ref<StorageLocationCreate & StorageLocationUpdate>({
  name: '',
  parent: null,
  is_member: false,
  member: null
})

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const isEdit = computed(() => !!props.location)

const isValid = computed(() => {
  if (!form.value.name) return false
  if (form.value.is_member && !form.value.member) return false
  return true
})

// Filter out the current location and its children from parent options
const parentOptions = computed(() => {
  return inventoryStore.locations
    .filter((l) => {
      // Can't be its own parent
      if (props.location && l.id === props.location.id) return false
      // Can't be a member location as parent
      if (l.is_member) return false
      return true
    })
    .map((l) => ({
      value: l.id,
      label: l.full_path || l.name
    }))
})

const memberOptions = computed(() => membersStore.memberOptions)

// Initialize form from props
watch(
  () => props.modelValue,
  async (newVal) => {
    if (newVal) {
      // Load members if not loaded
      if (membersStore.members.length === 0) {
        await membersStore.fetchMembers({ limit: 1000 })
      }

      if (props.location) {
        form.value = {
          name: props.location.name,
          parent: props.location.parent,
          is_member: props.location.is_member,
          member: props.location.member
        }
      } else {
        form.value = {
          name: '',
          parent: props.defaultParent || null,
          is_member: false,
          member: null
        }
      }
    }
  },
  { immediate: true }
)

// Clear member when is_member is unchecked
watch(
  () => form.value.is_member,
  (isMember) => {
    if (!isMember) {
      form.value.member = null
    }
  }
)

function closeDialog() {
  visible.value = false
}

async function submit() {
  if (!isValid.value) return

  loading.value = true
  try {
    let result: StorageLocation

    const data = {
      name: form.value.name,
      parent: form.value.parent || null,
      is_member: form.value.is_member,
      member: form.value.is_member ? form.value.member : null
    }

    if (isEdit.value && props.location) {
      result = await inventoryStore.updateLocation(props.location.id, data)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Lagerort wurde aktualisiert',
        life: 3000
      })
    } else {
      result = await inventoryStore.createLocation(data as StorageLocationCreate)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Lagerort wurde erstellt',
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
.location-form {
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

.text-muted {
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}

.w-full {
  width: 100%;
}

.flex {
  display: flex;
}

.align-items-center {
  align-items: center;
}

.gap-2 {
  gap: 0.5rem;
}
</style>
