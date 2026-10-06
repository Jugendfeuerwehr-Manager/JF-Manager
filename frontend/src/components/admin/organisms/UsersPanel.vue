<template>
  <div class="users-panel" :class="{ 'mobile': isMobile }">
    <!-- Master list (hidden on mobile when detail is open) -->
    <div
      class="master-pane"
      :class="{ 'hidden-mobile': isMobile && selectedUserId !== null }"
    >
      <Toolbar class="mb-3">
        <template #start>
          <InputText
            v-model="search"
            placeholder="Suchen..."
            size="small"
            class="mr-2"
            @input="handleSearch"
          />
        </template>
        <template #end>
          <Button
            v-if="authStore.user?.is_superuser"
            icon="pi pi-plus"
            label="Neu"
            size="small"
            @click="openNew"
          />
        </template>
      </Toolbar>

      <div v-if="adminStore.usersLoading" class="flex justify-content-center py-6">
        <ProgressSpinner style="width: 32px; height: 32px" stroke-width="4" />
      </div>

      <div v-else class="user-list">
        <div
          v-for="user in adminStore.users"
          :key="user.id"
          class="user-list-item"
          :class="{ 'active': selectedUserId === user.id }"
          @click="selectUser(user.id)"
        >
          <div class="flex align-items-center gap-2">
            <Avatar
              :label="userInitials(user)"
              shape="circle"
              size="normal"
              :style="{ 'background-color': userColor(user), color: '#fff' }"
            />
            <div class="flex-1 min-w-0">
              <div class="font-medium text-sm truncate">
                {{ user.full_name || user.username }}
              </div>
              <div class="text-xs text-color-secondary truncate">{{ user.username }}</div>
            </div>
            <div class="flex flex-column align-items-end gap-1">
              <Tag
                v-if="user.is_superuser"
                value="Super"
                severity="danger"
                class="text-xs"
              />
              <Tag
                v-else-if="user.is_staff"
                value="Staff"
                severity="warn"
                class="text-xs"
              />
              <Tag
                v-if="user.mfa_enabled"
                value="2FA"
                severity="success"
                icon="pi pi-shield"
                class="text-xs"
              />
              <Tag
                v-if="!user.is_active"
                value="Inaktiv"
                severity="secondary"
                class="text-xs"
              />
            </div>
          </div>
        </div>

        <div v-if="adminStore.users.length === 0" class="master-empty">
          <div class="master-empty-icon"><i class="pi pi-users" /></div>
          <div class="master-empty-text">Keine Benutzer gefunden</div>
          <div class="master-empty-sub">Erstelle einen Benutzer mit dem + Button</div>
        </div>
      </div>
    </div>

    <!-- Detail pane -->
    <div
      class="detail-pane"
      :class="{ 'hidden-mobile': isMobile && selectedUserId === null && !showNew }"
    >
      <!-- Mobile back button -->
      <Button
        v-if="isMobile"
        icon="pi pi-arrow-left"
        label="Zurück"
        text
        size="small"
        class="mb-3"
        @click="closeDetail"
      />

      <div v-if="detailLoading" class="flex justify-content-center py-6">
        <ProgressSpinner style="width: 32px; height: 32px" stroke-width="4" />
      </div>

      <UserDetailForm
        v-else-if="showForm"
        :user="selectedUserDetail"
        @saved="handleSaved"
        @cancel="handleCancel"
      />

      <div v-else class="detail-empty">
        <div class="detail-empty-illustration">
          <div class="detail-empty-circle">
            <i class="pi pi-user" />
          </div>
        </div>
        <h3 class="detail-empty-title">Kein Benutzer ausgewählt</h3>
        <p class="detail-empty-sub">Wähle einen Benutzer aus der Liste oder lege einen neuen an.</p>
        <Button
          v-if="authStore.user?.is_superuser"
          label="Neuen Benutzer anlegen"
          icon="pi pi-plus"
          size="small"
          @click="openNew"
        />
      </div>

      <!-- Second factor (SEC-11.7) -->
      <section
        v-if="authStore.user?.is_superuser && selectedUserId !== null && !showNew && !detailLoading && selectedUserDetail?.mfa"
        class="mfa-admin mt-4"
        aria-labelledby="mfa-admin-heading"
      >
        <h4 id="mfa-admin-heading" class="m-0"><i class="pi pi-shield" aria-hidden="true" /> Zwei-Faktor-Anmeldung</h4>
        <p class="text-sm m-0">{{ mfaSummary }}</p>
        <p v-if="selectedUserDetail.mfa.reset_blocker === 'console_only'" class="text-sm text-color-secondary m-0">
          Administrationskonto: Zurücksetzen nur auf dem Server mit
          <code>jfctl admin reset-mfa --user {{ selectedUserDetail.username }}</code>.
        </p>
        <p v-else-if="selectedUserDetail.mfa.reset_blocker === 'self'" class="text-sm text-color-secondary m-0">
          Die eigene Zwei-Faktor-Anmeldung verwaltest du im Profil.
        </p>
        <Button
          v-if="selectedUserDetail.mfa.enabled && selectedUserDetail.mfa.ui_reset_allowed"
          icon="pi pi-refresh"
          label="Zwei-Faktor-Anmeldung zurücksetzen"
          severity="warn"
          outlined
          size="small"
          class="align-self-start"
          @click="confirmResetMfa"
        />
      </section>

      <!-- Actions footer for existing users -->
      <div
        v-if="authStore.user?.is_superuser && selectedUserId !== null && !showNew && !detailLoading && selectedUserDetail"
        class="detail-footer flex justify-content-end gap-2 mt-4 pt-3"
      >
        <Button
          v-if="selectedUserDetail.is_active"
          icon="pi pi-ban"
          label="Deaktivieren"
          severity="warn"
          :disabled="selectedUserId === usersStore.currentUser?.id"
          text
          size="small"
          @click="confirmDeactivate"
        />
        <Button
          v-else
          icon="pi pi-check-circle"
          label="Aktivieren"
          severity="success"
          text
          size="small"
          @click="activateUser"
        />
        <Button
          icon="pi pi-trash"
          label="Benutzer löschen"
          severity="danger"
          :disabled="selectedUserId === usersStore.currentUser?.id"
          text
          size="small"
          @click="confirmDelete"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAdminStore } from '@/stores/admin'
import { useUsersStore } from '@/stores/users'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import Toolbar from 'primevue/toolbar'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import ProgressSpinner from 'primevue/progressspinner'
import Avatar from 'primevue/avatar'
import Tag from 'primevue/tag'
import UserDetailForm from '@/components/admin/molecules/UserDetailForm.vue'
import type { AdminUserDetail, AdminUser } from '@/types/admin'
import { getApiErrorMessage } from '@/utils/apiError'

const adminStore = useAdminStore()
const authStore = useAuthStore()
const usersStore = useUsersStore()
const confirm = useConfirm()
const toast = useToast()

const search = ref('')
const selectedUserId = ref<number | null>(null)
const selectedUserDetail = ref<AdminUserDetail | null>(null)
const detailLoading = ref(false)
const showNew = ref(false)

const isMobile = ref(window.innerWidth < 768)

window.addEventListener('resize', () => {
  isMobile.value = window.innerWidth < 768
})

const showForm = computed(() => showNew.value || selectedUserId.value !== null)

function userInitials(user: AdminUser): string {
  if (user.first_name && user.last_name)
    return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase()
  return user.username.slice(0, 2).toUpperCase()
}

function userColor(user: AdminUser): string {
  const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6']
  const idx = user.id % colors.length
  return colors[idx] ?? '#6366f1'
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null

function handleSearch() {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    adminStore.fetchUsers({ search: search.value, limit: 100 })
  }, 300)
}

async function selectUser(id: number) {
  selectedUserId.value = id
  showNew.value = false
  detailLoading.value = true
  selectedUserDetail.value = null
  try {
    selectedUserDetail.value = await adminStore.fetchUser(id)
  } finally {
    detailLoading.value = false
  }
}

function openNew() {
  selectedUserId.value = null
  selectedUserDetail.value = null
  showNew.value = true
}

function closeDetail() {
  selectedUserId.value = null
  showNew.value = false
  selectedUserDetail.value = null
}

async function handleSaved(userId: number) {
  showNew.value = false
  await adminStore.fetchUsers({ limit: 100 })
  await selectUser(userId)
}

function handleCancel() {
  if (showNew.value) {
    showNew.value = false
  }
  // keep selected user visible on cancel-edit
}

function confirmDeactivate() {
  confirm.require({
    message: `Benutzer "${selectedUserDetail.value?.username}" wirklich deaktivieren?`,
    header: 'Benutzer deaktivieren',
    icon: 'pi pi-ban',
    rejectLabel: 'Abbrechen',
    acceptLabel: 'Deaktivieren',
    acceptProps: { severity: 'warn' },
    accept: async () => {
      try {
        await adminStore.updateUser(selectedUserId.value!, { is_active: false })
        toast.add({ severity: 'success', summary: 'Deaktiviert', life: 3000 })
        await adminStore.fetchUsers({ limit: 100 })
        await selectUser(selectedUserId.value!)
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler beim Deaktivieren', life: 4000 })
      }
    },
  })
}

async function activateUser() {
  try {
    await adminStore.updateUser(selectedUserId.value!, { is_active: true })
    toast.add({ severity: 'success', summary: 'Aktiviert', life: 3000 })
    await adminStore.fetchUsers({ limit: 100 })
    await selectUser(selectedUserId.value!)
  } catch {
    toast.add({ severity: 'error', summary: 'Fehler beim Aktivieren', life: 4000 })
  }
}

const mfaSummary = computed(() => {
  const mfa = selectedUserDetail.value?.mfa
  if (!mfa?.enabled) return 'Nicht eingerichtet.'
  const parts = []
  if (mfa.totp) parts.push('Authenticator-App')
  if (mfa.passkeys) parts.push(mfa.passkeys === 1 ? '1 Passkey' : `${mfa.passkeys} Passkeys`)
  return `Aktiv: ${parts.join(', ')}.`
})

function confirmResetMfa() {
  const name = selectedUserDetail.value?.username
  confirm.require({
    message: `Zwei-Faktor-Anmeldung von "${name}" zurücksetzen? Authenticator-App, Passkeys und Wiederherstellungscodes werden entfernt und alle Sitzungen des Kontos beendet. Vorher die Identität der Person prüfen.`,
    header: 'Zwei-Faktor-Anmeldung zurücksetzen',
    icon: 'pi pi-shield',
    rejectLabel: 'Abbrechen',
    acceptLabel: 'Zurücksetzen',
    acceptProps: { severity: 'warn' },
    accept: async () => {
      try {
        await adminStore.resetUserMfa(selectedUserId.value!)
        toast.add({ severity: 'success', summary: 'Zwei-Faktor-Anmeldung zurückgesetzt', detail: `${name} richtet sie bei der nächsten Anmeldung neu ein.`, life: 5000 })
        await adminStore.fetchUsers({ limit: 100 })
        await selectUser(selectedUserId.value!)
      } catch (err) {
        toast.add({ severity: 'error', summary: 'Zurücksetzen fehlgeschlagen', detail: getApiErrorMessage(err, 'Bitte erneut versuchen.'), life: 6000 })
      }
    },
  })
}

function confirmDelete() {
  confirm.require({
    message: `Benutzer "${selectedUserDetail.value?.username}" wirklich endgültig löschen? Diese Aktion kann nicht rückgängig gemacht werden.`,
    header: 'Benutzer löschen',
    icon: 'pi pi-trash',
    rejectLabel: 'Abbrechen',
    acceptLabel: 'Endgültig löschen',
    acceptProps: { severity: 'danger' },
    accept: async () => {
      try {
        await adminStore.deleteUser(selectedUserId.value!)
        toast.add({ severity: 'success', summary: 'Gelöscht', life: 3000 })
        closeDetail()
        await adminStore.fetchUsers({ limit: 100 })
      } catch {
        toast.add({ severity: 'error', summary: 'Fehler beim Löschen', life: 4000 })
      }
    },
  })
}

onMounted(async () => {
  await adminStore.fetchUsers({ limit: 100 })
  await adminStore.fetchGroups({ limit: 200 })
  await usersStore.fetchCurrentUser()
})
</script>

<style scoped>
.mfa-admin {
  display: flex;
  flex-direction: column;
  gap: .5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border, #d9dee5);
}

.mfa-admin h4 {
  display: flex;
  align-items: center;
  gap: .5rem;
}

.users-panel {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1rem;
  height: 100%;
  min-height: 600px;
}

.users-panel.mobile {
  grid-template-columns: 1fr;
}

.master-pane {
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.master-pane .p-toolbar {
  border-radius: 0;
  border: none;
  border-bottom: 1px solid var(--p-content-border-color);
}

.user-list {
  overflow-y: auto;
  flex: 1;
  padding: 0.25rem;
}

.user-list-item {
  padding: 0.625rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.user-list-item:hover {
  background: var(--p-content-hover-background);
}

.user-list-item.active {
  background: var(--p-primary-50, #eff6ff);
  border-left: 3px solid var(--p-primary-color);
}

.detail-pane {
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
  padding: 1.25rem;
  overflow-y: auto;
}

.empty-detail {
  height: 100%;
}

.hidden-mobile {
  display: none;
}

.detail-footer {
  border-top: 1px solid var(--p-content-border-color);
}

.master-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  color: var(--p-text-muted-color);
}

.master-empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--p-content-hover-background);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  margin-bottom: 0.75rem;
}

.master-empty-text {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 0.25rem;
}

.master-empty-sub {
  font-size: 0.8rem;
  opacity: 0.7;
}

.detail-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  text-align: center;
  padding: 2rem;
}

.detail-empty-illustration {
  margin-bottom: 1.5rem;
}

.detail-empty-circle {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--p-primary-100, #dbeafe), var(--p-primary-200, #bfdbfe));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.5rem;
  color: var(--p-primary-500, #3b82f6);
  margin: 0 auto;
}

.detail-empty-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--p-text-color);
  margin: 0 0 0.5rem;
}

.detail-empty-sub {
  font-size: 0.875rem;
  color: var(--p-text-muted-color);
  margin: 0 0 1.5rem;
  max-width: 260px;
}

.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
