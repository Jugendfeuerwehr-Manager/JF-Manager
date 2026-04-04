<template>
  <form class="group-detail-form" @submit.prevent="handleSubmit">
    <!-- Header -->
    <div class="form-header flex align-items-center justify-between mb-4">
      <div class="flex align-items-center gap-2">
        <i class="pi pi-users text-xl text-primary" />
        <h3 class="m-0">
          {{ isNew ? 'Neue Gruppe' : (localData.name || 'Gruppe bearbeiten') }}
        </h3>
      </div>
      <div class="flex gap-2 ml-auto">
        <Button
          type="button"
          label="Abbrechen"
          severity="secondary"
          size="small"
          @click="emit('cancel')"
        />
        <Button
          type="submit"
          :label="isNew ? 'Erstellen' : 'Speichern'"
          icon="pi pi-check"
          size="small"
          :loading="saving"
        />
      </div>
    </div>

    <div v-if="errorMessage" class="mb-3">
      <Message severity="error" :closable="false">{{ errorMessage }}</Message>
    </div>

    <!-- Name -->
    <div class="field mb-4">
      <label for="group-name" class="required">Gruppenname</label>
      <InputText id="group-name" v-model="localData.name" class="w-full" required />
    </div>

    <!-- Permissions -->
    <Fieldset legend="Berechtigungen" :toggleable="false">
      <div v-if="permissionsLoading" class="flex justify-content-center py-4">
        <ProgressSpinner style="width: 32px; height: 32px" stroke-width="4" />
      </div>
      <PermissionPicker
        v-else
        v-model="localData.permission_ids"
        :categories="permissionCategories"
      />
    </Fieldset>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'
import InputText from 'primevue/inputtext'
import Fieldset from 'primevue/fieldset'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import PermissionPicker from '@/components/admin/molecules/PermissionPicker.vue'
import type { AuthGroupDetail, AuthGroupWrite } from '@/types/admin'

interface Props {
  group?: AuthGroupDetail | null
}

const props = withDefaults(defineProps<Props>(), { group: null })

const emit = defineEmits<{
  saved: [groupId: number]
  cancel: []
}>()

const adminStore = useAdminStore()
const permissionCategories = computed(() => adminStore.permissionCategories)
const permissionsLoading = computed(() => adminStore.permissionsLoading)

const saving = ref(false)
const errorMessage = ref('')

const isNew = computed(() => !props.group)

function buildDefault(): AuthGroupWrite {
  return { name: '', permission_ids: [] }
}

function fromGroup(g: AuthGroupDetail): AuthGroupWrite {
  return {
    name: g.name,
    permission_ids: g.permissions.map((p) => p.id),
  }
}

const localData = ref<AuthGroupWrite>(props.group ? fromGroup(props.group) : buildDefault())

watch(
  () => props.group,
  (g) => {
    localData.value = g ? fromGroup(g) : buildDefault()
    errorMessage.value = ''
  }
)

onMounted(() => adminStore.fetchPermissions())

async function handleSubmit() {
  saving.value = true
  errorMessage.value = ''
  try {
    let savedId: number
    if (isNew.value) {
      const created = await adminStore.createGroup(localData.value)
      savedId = created.id
    } else {
      const updated = await adminStore.updateGroup(props.group!.id, localData.value)
      savedId = updated.id
      await adminStore.fetchGroups()
    }
    emit('saved', savedId)
  } catch (err: unknown) {
    const e = err as { response?: { data?: Record<string, unknown> } }
    if (e?.response?.data) {
      const messages = Object.entries(e.response.data)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join('\n')
      errorMessage.value = messages
    } else {
      errorMessage.value = 'Fehler beim Speichern.'
    }
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.group-detail-form {
  padding: 0;
}

.form-header {
  position: sticky;
  top: 0;
  background: var(--p-content-background);
  z-index: 1;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--p-content-border-color);
  margin-bottom: 1rem;
  width: 100%;
  box-sizing: border-box;
}

label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 0.25rem;
  color: var(--p-text-color);
}

label.required::after {
  content: ' *';
  color: var(--p-red-500);
}
</style>
