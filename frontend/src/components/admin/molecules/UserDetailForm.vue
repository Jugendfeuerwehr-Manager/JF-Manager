<template>
  <form class="user-detail-form" @submit.prevent="handleSubmit">
    <!-- Header -->
    <div class="form-header flex align-items-center justify-between mb-4">
      <div class="flex align-items-center gap-2">
        <i class="pi pi-user text-xl text-primary" />
        <h3 class="m-0">
          {{ isNew ? 'Neuer Benutzer' : `${localData.first_name} ${localData.last_name}`.trim() || localData.username }}
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

    <!-- Basic Info -->
    <Fieldset legend="Grundinformationen" :toggleable="false" class="mb-3">
      <div class="formgrid grid">
        <div class="field col-12 md:col-6">
          <label for="username" class="required">Benutzername</label>
          <InputText id="username" v-model="localData.username" class="w-full" required />
        </div>
        <div class="field col-12 md:col-6">
          <label for="email">E-Mail</label>
          <InputText id="email" v-model="localData.email" type="email" class="w-full" />
        </div>
        <div class="field col-12 md:col-6">
          <label for="first_name">Vorname</label>
          <InputText id="first_name" v-model="localData.first_name" class="w-full" />
        </div>
        <div class="field col-12 md:col-6">
          <label for="last_name">Nachname</label>
          <InputText id="last_name" v-model="localData.last_name" class="w-full" />
        </div>
      </div>
    </Fieldset>

    <!-- Contact -->
    <Fieldset legend="Kontakt" :toggleable="true" :collapsed="!hasContactData" class="mb-3">
      <div class="formgrid grid">
        <div class="field col-12 md:col-6">
          <label for="phone">Telefon</label>
          <InputText id="phone" v-model="localData.phone" class="w-full" />
        </div>
        <div class="field col-12 md:col-6">
          <label for="mobile_phone">Mobiltelefon</label>
          <InputText id="mobile_phone" v-model="localData.mobile_phone" class="w-full" />
        </div>
        <div class="field col-12">
          <label for="street">Straße</label>
          <InputText id="street" v-model="localData.street" class="w-full" />
        </div>
        <div class="field col-12 md:col-4">
          <label for="zip_code">PLZ</label>
          <InputText id="zip_code" v-model="localData.zip_code" class="w-full" />
        </div>
        <div class="field col-12 md:col-8">
          <label for="city">Stadt</label>
          <InputText id="city" v-model="localData.city" class="w-full" />
        </div>
      </div>
    </Fieldset>

    <!-- Account Settings -->
    <Fieldset legend="Konto & Berechtigungen" :toggleable="false" class="mb-3">
      <div class="formgrid grid">
        <div class="field col-12 md:col-4 flex align-items-center gap-2">
          <Checkbox v-model="localData.is_active" input-id="is_active" binary />
          <label for="is_active">Aktiv</label>
        </div>
        <div class="field col-12 md:col-4 flex align-items-center gap-2">
          <Checkbox v-model="localData.is_staff" input-id="is_staff" binary />
          <label for="is_staff">
            Staf-Benutzer
            <PermissionInfoIcon description="Kann sich am Admin-Interface anmelden." />
          </label>
        </div>
        <div class="field col-12 md:col-4 flex align-items-center gap-2">
          <Checkbox
            v-model="localData.is_superuser"
            input-id="is_superuser"
            binary
            :disabled="isSelfSuperuser"
          />
          <label for="is_superuser">
            Superuser
            <PermissionInfoIcon description="Hat alle Berechtigungen ohne explizite Zuweisung." />
          </label>
          <small v-if="isSelfSuperuser" class="text-color-secondary">(eigener Account)</small>
        </div>

        <!-- Groups -->
        <div class="field col-12">
          <label>Gruppen</label>
          <MultiSelect
            v-model="localData.group_ids"
            :options="groups"
            option-label="name"
            option-value="id"
            placeholder="Gruppen auswählen..."
            class="w-full"
            display="chip"
            :loading="groupsLoading"
          />
        </div>
      </div>
    </Fieldset>

    <!-- DSGVO & Signature -->
    <Fieldset legend="DSGVO & Signatur" :toggleable="true" :collapsed="true" class="mb-3">
      <div class="formgrid grid">
        <div class="field col-12 md:col-6 flex align-items-center gap-2">
          <Checkbox v-model="localData.dsgvo_internal" input-id="dsgvo_internal" binary />
          <label for="dsgvo_internal">
            DSGVO intern
            <PermissionInfoIcon description="Einwilligung zur internen Datenweitergabe." />
          </label>
        </div>
        <div class="field col-12 md:col-6 flex align-items-center gap-2">
          <Checkbox v-model="localData.dsgvo_external" input-id="dsgvo_external" binary />
          <label for="dsgvo_external">
            DSGVO extern
            <PermissionInfoIcon description="Einwilligung zur externen Datenweitergabe." />
          </label>
        </div>
        <div class="field col-12">
          <label>E-Mail Signatur</label>
          <p class="text-xs text-color-secondary mt-0 mb-2">Wird automatisch an System-E-Mails angehängt.</p>
          <TiptapEditor
            :model-value="localData.email_signature ?? ''"
            @update:model-value="localData.email_signature = $event"
            placeholder="Signatur eingeben..."
            :show-variables="false"
          />
        </div>
      </div>
    </Fieldset>

    <!-- Password -->
    <Fieldset
      :legend="isNew ? 'Passwort' : 'Passwort ändern'"
      :toggleable="!isNew"
      :collapsed="!isNew ? true : false"
      class="mb-3"
    >
      <div class="formgrid grid">
        <div class="field col-12 md:col-6">
          <label :class="{ required: isNew }">
            {{ isNew ? 'Passwort' : 'Neues Passwort' }}
          </label>
          <Password
            v-model="localData.password"
            class="w-full"
            :required="isNew"
            toggle-mask
            :feedback="true"
            :input-props="{ autocomplete: 'new-password', class: 'w-full' }"
          />
        </div>
      </div>
    </Fieldset>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useAdminStore } from '@/stores/admin'
import { useAuthStore } from '@/stores/auth'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'
import MultiSelect from 'primevue/multiselect'
import Password from 'primevue/password'
import Fieldset from 'primevue/fieldset'
import Button from 'primevue/button'
import Message from 'primevue/message'
import PermissionInfoIcon from '@/components/admin/atoms/PermissionInfoIcon.vue'
import TiptapEditor from '@/components/emails/organisms/TiptapEditor.vue'
import type { AdminUserDetail, AdminUserWrite } from '@/types/admin'

interface Props {
  user?: AdminUserDetail | null
}

const props = withDefaults(defineProps<Props>(), { user: null })

const emit = defineEmits<{
  saved: [userId: number]
  cancel: []
}>()

const adminStore = useAdminStore()
const authStore = useAuthStore()

const groups = computed(() => adminStore.groups)
const groupsLoading = computed(() => adminStore.groupsLoading)

const saving = ref(false)
const errorMessage = ref('')

const isNew = computed(() => !props.user)

const isSelfSuperuser = computed(() => {
  const me = authStore.user
  return !isNew.value && me?.id === props.user?.id && me?.is_superuser === true
})

const hasContactData = computed(() => {
  const u = props.user
  if (!u) return false
  return !!(u.phone || u.mobile_phone || u.street || u.zip_code || u.city)
})

function buildDefault(): AdminUserWrite & { password?: string } {
  return {
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    mobile_phone: '',
    street: '',
    zip_code: '',
    city: '',
    is_staff: false,
    is_active: true,
    is_superuser: false,
    dsgvo_internal: false,
    dsgvo_external: false,
    email_signature: '',
    theme_mode: '',
    group_ids: [],
    password: '',
  }
}

function fromUser(u: AdminUserDetail): AdminUserWrite & { password?: string } {
  return {
    username: u.username,
    email: u.email,
    first_name: u.first_name,
    last_name: u.last_name,
    phone: u.phone ?? '',
    mobile_phone: u.mobile_phone ?? '',
    street: u.street ?? '',
    zip_code: u.zip_code ?? '',
    city: u.city ?? '',
    is_staff: u.is_staff,
    is_active: u.is_active,
    is_superuser: u.is_superuser,
    dsgvo_internal: u.dsgvo_internal ?? false,
    dsgvo_external: u.dsgvo_external ?? false,
    email_signature: u.email_signature ?? '',
    theme_mode: u.theme_mode ?? '',
    group_ids: u.groups.map((g) => g.id),
    password: '',
  }
}

const localData = ref<AdminUserWrite & { password?: string }>(
  props.user ? fromUser(props.user) : buildDefault()
)

watch(
  () => props.user,
  (u) => {
    localData.value = u ? fromUser(u) : buildDefault()
    errorMessage.value = ''
  }
)

async function handleSubmit() {
  saving.value = true
  errorMessage.value = ''
  try {
    const payload: AdminUserWrite = { ...localData.value }
    // strip empty password
    if (!payload.password) {
      delete payload.password
    }
    let savedId: number
    if (isNew.value) {
      const created = await adminStore.createUser(payload)
      savedId = created.id
    } else {
      const updated = await adminStore.updateUser(props.user!.id, payload)
      savedId = updated.id
      // Refresh list
      await adminStore.fetchUsers()
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
.user-detail-form {
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
