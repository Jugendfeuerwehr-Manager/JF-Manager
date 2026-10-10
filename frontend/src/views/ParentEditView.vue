<template>
  <div class="parent-edit">
    <StateView v-if="loadState === 'loading'" kind="loading" title="Elternteil wird geladen …" />
    <StateView
      v-else-if="loadState"
      :kind="loadState"
      :title="loadState === 'forbidden' ? 'Keine Berechtigung für diesen Kontakt' : 'Elternteil konnte nicht geladen werden'"
      :retry="loadState !== 'forbidden'"
      @retry="load"
    >
      <router-link to="/parents" class="text-link">Zur Elternliste</router-link>
    </StateView>

    <template v-else>
      <nav aria-label="Brotkrumen" class="breadcrumb">
        <router-link to="/parents">Eltern</router-link>
        <i class="pi pi-angle-right" aria-hidden="true"></i>
        <span aria-current="page">{{ isEditMode ? `${savedName} bearbeiten` : 'Neu' }}</span>
      </nav>

      <header class="edit-head">
        <h1>{{ isEditMode ? 'Elternteil bearbeiten' : 'Elternteil anlegen' }}</h1>
        <StatusBadge v-if="isDirty" severity="warning" icon="pi pi-pencil" label="Ungespeicherte Änderungen" />
      </header>

      <ParentPortalAccessCard v-if="isEditMode" :parent-id="parentId" />

      <section v-if="isEditMode && canLinkAccounts" class="form-card account-link">
        <AccountLinkCard kind="parent" :record-id="parentId" :record-name="`${formData.name} ${formData.lastname}`.trim()" />
      </section>

      <form id="parent-form" class="edit-form" novalidate @submit.prevent="handleSubmit">
        <section class="form-card" aria-labelledby="parent-name-title">
          <h2 id="parent-name-title">Name</h2>
          <div class="form-grid">
            <div v-for="field in nameFields" :key="field.id" class="field">
              <label :for="field.id">{{ field.label }}</label>
              <InputText
                :id="field.id"
                v-model="formData[field.id]"
                :invalid="!!errors[field.id]"
                :aria-invalid="!!errors[field.id] || undefined"
                :aria-describedby="errors[field.id] ? `${field.id}-error` : undefined"
                :autocomplete="field.autocomplete"
              />
              <p v-if="errors[field.id]" :id="`${field.id}-error`" class="field__error">
                <i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors[field.id] }}
              </p>
            </div>
          </div>
        </section>

        <section class="form-card" aria-labelledby="parent-contact-title">
          <h2 id="parent-contact-title">Kontakt</h2>
          <div class="form-grid">
            <div v-for="field in contactFields" :key="field.id" class="field">
              <label :for="field.id">{{ field.label }}<span v-if="field.optional" class="field__optional"> (optional)</span></label>
              <InputText
                :id="field.id"
                v-model="formData[field.id]"
                :type="field.type"
                :inputmode="field.inputmode"
                :invalid="!!errors[field.id]"
                :aria-invalid="!!errors[field.id] || undefined"
                :aria-describedby="errors[field.id] ? `${field.id}-error` : undefined"
              />
              <p v-if="errors[field.id]" :id="`${field.id}-error`" class="field__error">
                <i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors[field.id] }}
              </p>
            </div>
          </div>
        </section>

        <section class="form-card" aria-labelledby="parent-address-title">
          <h2 id="parent-address-title">Adresse</h2>
          <div class="form-grid">
            <div v-for="field in addressFields" :key="field.id" class="field" :class="{ 'field--wide': field.wide }">
              <label :for="field.id">{{ field.label }}<span class="field__optional"> (optional)</span></label>
              <InputText
                :id="field.id"
                v-model="formData[field.id]"
                :invalid="!!errors[field.id]"
                :aria-invalid="!!errors[field.id] || undefined"
                :aria-describedby="errors[field.id] ? `${field.id}-error` : undefined"
              />
              <p v-if="errors[field.id]" :id="`${field.id}-error`" class="field__error">
                <i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors[field.id] }}
              </p>
            </div>
          </div>
        </section>

        <section class="form-card" aria-labelledby="parent-children-title">
          <h2 id="parent-children-title">Verknüpfte Mitglieder</h2>
          <div class="field field--wide">
            <label for="children">Mitglieder</label>
            <MultiSelect
              v-model="formData.children"
              input-id="children"
              :options="parentsStore.childOptions"
              option-label="label"
              option-value="value"
              placeholder="Mitglieder auswählen"
              :loading="parentsStore.childOptionsLoading"
              filter
              display="chip"
              :max-selected-labels="3"
              :invalid="!!errors.children"
              :aria-describedby="errors.children ? 'children-error' : undefined"
            />
            <p v-if="errors.children" id="children-error" class="field__error">
              <i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors.children }}
            </p>
          </div>
        </section>

        <section class="form-card" aria-labelledby="parent-notes-title">
          <h2 id="parent-notes-title">Notizen</h2>
          <div class="field field--wide">
            <label for="notes">Notizen<span class="field__optional"> (optional)</span></label>
            <Textarea id="notes" v-model="formData.notes" rows="4" auto-resize />
          </div>
        </section>
      </form>

      <div class="action-bar">
        <p class="action-bar__status" :class="{ 'action-bar__status--error': errorCount }" role="status">
          <template v-if="errorCount">
            <i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errorCount === 1 ? '1 Feld braucht' : `${errorCount} Felder brauchen` }} deine Aufmerksamkeit
          </template>
          <template v-else-if="submitError">
            <i class="pi pi-exclamation-circle" aria-hidden="true"></i>Nicht gespeichert: {{ submitError }}
          </template>
          <template v-else-if="isDirty">
            <i class="pi pi-pencil" aria-hidden="true"></i>Ungespeicherte Änderungen
          </template>
          <template v-else-if="isEditMode">
            <i class="pi pi-check" aria-hidden="true"></i>Keine Änderungen
          </template>
        </p>
        <div class="action-bar__buttons">
          <Button label="Abbrechen" severity="secondary" text type="button" :disabled="saving" @click="router.push('/parents')" />
          <Button
            :label="isEditMode ? 'Änderungen speichern' : 'Elternteil anlegen'"
            icon="pi pi-check"
            type="submit"
            form="parent-form"
            :loading="saving"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import MultiSelect from 'primevue/multiselect'
import Textarea from 'primevue/textarea'
import StateView, { stateForError, type StateKind } from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useParentsStore } from '@/stores/parents'
import type { ParentCreate } from '@/types/parents'
import { classifyApiError, getApiErrorMessage } from '@/utils/apiError'
import ParentPortalAccessCard from '@/views/portal-admin/ParentPortalAccessCard.vue'
import AccountLinkCard from '@/components/members/organisms/AccountLinkCard.vue'
import { useAuthStore } from '@/stores/auth'

type TextField = 'name' | 'lastname' | 'email' | 'email2' | 'phone' | 'mobile' | 'street' | 'zip_code' | 'city'
type ErrorField = TextField | 'children' | 'notes'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const parentsStore = useParentsStore()

const parentId = computed(() => Number(route.params.id))
const isEditMode = computed(() => !!route.params.id)
// Account management links staff accounts to parent records (PORTAL-04, Q4).
const canLinkAccounts = computed(() => useAuthStore().hasPerm('users.change_customuser'))

const nameFields: { id: TextField; label: string; autocomplete: string }[] = [
  { id: 'name', label: 'Vorname', autocomplete: 'off' },
  { id: 'lastname', label: 'Nachname', autocomplete: 'off' },
]
const contactFields: { id: TextField; label: string; type: string; inputmode?: 'email' | 'tel'; optional?: boolean }[] = [
  { id: 'email', label: 'E-Mail', type: 'email', inputmode: 'email' },
  { id: 'email2', label: 'Weitere E-Mail', type: 'email', inputmode: 'email', optional: true },
  { id: 'phone', label: 'Telefon', type: 'tel', inputmode: 'tel', optional: true },
  { id: 'mobile', label: 'Mobil', type: 'tel', inputmode: 'tel', optional: true },
]
const addressFields: { id: TextField; label: string; wide?: boolean }[] = [
  { id: 'street', label: 'Straße', wide: true },
  { id: 'zip_code', label: 'PLZ' },
  { id: 'city', label: 'Ort' },
]
const FIELD_ORDER: ErrorField[] = ['name', 'lastname', 'email', 'email2', 'phone', 'mobile', 'street', 'zip_code', 'city', 'children', 'notes']

const formData = reactive<Required<ParentCreate>>({
  name: '',
  lastname: '',
  email: '',
  email2: '',
  phone: '',
  mobile: '',
  street: '',
  zip_code: '',
  city: '',
  notes: '',
  children: [],
})
const errors = reactive<Partial<Record<ErrorField, string>>>({})
const loadState = ref<StateKind | null>(isEditMode.value ? 'loading' : null)
const saving = ref(false)
const submitError = ref('')
const savedSnapshot = ref('')
const savedName = ref('')
/** Set after a successful save so the leave guard lets the navigation through. */
let leavingAfterSave = false

const snapshot = () => JSON.stringify(formData)
const isDirty = computed(() => savedSnapshot.value !== '' && snapshot() !== savedSnapshot.value)
const errorCount = computed(() => Object.values(errors).filter(Boolean).length)

function clearErrors() {
  for (const key of Object.keys(errors) as ErrorField[]) delete errors[key]
}

async function load() {
  parentsStore.fetchChildOptions().catch(() => {
    errors.children = 'Mitglieder konnten nicht geladen werden.'
  })
  if (!isEditMode.value) {
    savedSnapshot.value = snapshot()
    return
  }
  loadState.value = 'loading'
  try {
    const parent = await parentsStore.fetchParentById(parentId.value)
    Object.assign(formData, {
      name: parent.name ?? '',
      lastname: parent.lastname ?? '',
      email: parent.email ?? '',
      email2: parent.email2 ?? '',
      phone: parent.phone ?? '',
      mobile: parent.mobile ?? '',
      street: parent.street ?? '',
      zip_code: parent.zip_code ?? '',
      city: parent.city ?? '',
      notes: parent.notes ?? '',
      children: [...(parent.children ?? [])],
    })
    savedName.value = parent.full_name || `${parent.name} ${parent.lastname}`.trim()
    savedSnapshot.value = snapshot()
    loadState.value = null
  } catch (error) {
    loadState.value = stateForError(classifyApiError(error))
  }
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validateForm(): boolean {
  clearErrors()
  if (!formData.name.trim()) errors.name = 'Vorname ist erforderlich'
  if (!formData.lastname.trim()) errors.lastname = 'Nachname ist erforderlich'
  if (!formData.email.trim()) errors.email = 'E-Mail ist erforderlich'
  else if (!EMAIL_PATTERN.test(formData.email.trim())) errors.email = 'Bitte eine gültige E-Mail-Adresse eingeben'
  if (formData.email2.trim() && !EMAIL_PATTERN.test(formData.email2.trim())) errors.email2 = 'Bitte eine gültige E-Mail-Adresse eingeben'
  return errorCount.value === 0
}

function focusFirstError() {
  const first = FIELD_ORDER.find((field) => errors[field])
  if (!first) return
  const input = document.getElementById(first)
  input?.scrollIntoView?.({ behavior: 'smooth', block: 'center' })
  input?.focus({ preventScroll: true })
}

/** Puts server-side field errors next to the field instead of a toast. */
function applyServerErrors(error: unknown): boolean {
  const data = (error as { response?: { status?: number; data?: Record<string, unknown> } }).response?.data
  if (!data || typeof data !== 'object') return false
  let applied = false
  for (const field of FIELD_ORDER) {
    const value = data[field]
    const message = Array.isArray(value) ? value[0] : value
    if (typeof message === 'string') {
      errors[field] = message
      applied = true
    }
  }
  return applied
}

async function handleSubmit() {
  submitError.value = ''
  if (!validateForm()) {
    await nextTick()
    focusFirstError()
    return
  }

  saving.value = true
  try {
    const payload: ParentCreate = { ...formData, children: [...formData.children] }
    if (isEditMode.value) {
      await parentsStore.updateParent(parentId.value, payload)
      toast.add({ severity: 'success', summary: 'Gespeichert', detail: 'Elternteil wurde aktualisiert', life: 3000 })
    } else {
      await parentsStore.createParent(payload)
      toast.add({ severity: 'success', summary: 'Angelegt', detail: 'Elternteil wurde angelegt', life: 3000 })
    }
    savedSnapshot.value = snapshot()
    leavingAfterSave = true
    router.push('/parents')
  } catch (error) {
    if (applyServerErrors(error)) {
      await nextTick()
      focusFirstError()
    } else {
      submitError.value = getApiErrorMessage(error, 'Unbekannter Fehler')
    }
  } finally {
    saving.value = false
  }
}

function onBeforeUnload(event: BeforeUnloadEvent) {
  if (!isDirty.value) return
  event.preventDefault()
  event.returnValue = ''
}

onBeforeRouteLeave(() => leavingAfterSave || !isDirty.value || window.confirm('Ungespeicherte Änderungen verwerfen und die Seite verlassen?'))

onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
  load()
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', onBeforeUnload))
</script>

<style scoped>
.parent-edit {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-3);
  max-width: 960px;
  margin: 0 auto;
}

.breadcrumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.breadcrumb a,
.text-link {
  color: var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.breadcrumb i {
  font-size: 0.75rem;
}

.edit-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1-5);
}

.edit-head h1 {
  margin: 0;
  font-size: var(--jf-text-2xl);
  line-height: var(--jf-leading-tight);
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  padding: var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
}

.form-card h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-semibold);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--jf-space-2) 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.field--wide {
  grid-column: 1 / -1;
}

.field label {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}

.field__optional {
  font-weight: 400;
  color: var(--jf-color-text-muted);
}

.field :deep(.p-inputtext),
.field :deep(.p-multiselect),
.field :deep(.p-textarea) {
  width: 100%;
  min-height: var(--jf-touch-target);
}

.field__error {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 0.8125rem;
  font-weight: var(--jf-weight-semibold);
  color: var(--p-red-700);
}

.app-dark .field__error {
  color: var(--p-red-300);
}

.action-bar {
  position: sticky;
  bottom: 0;
  z-index: 5;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  background: var(--jf-color-card);
  border-top: 1px solid var(--jf-color-border);
}

.action-bar__status {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.action-bar__status--error {
  color: var(--p-red-700);
  font-weight: var(--jf-weight-semibold);
}

.app-dark .action-bar__status--error {
  color: var(--p-red-300);
}

.action-bar__buttons {
  display: flex;
  gap: var(--jf-space-1);
  margin-left: auto;
}

.action-bar__buttons :deep(.p-button) {
  min-height: var(--jf-touch-target);
}

@media (max-width: 1023px) {
  .action-bar {
    bottom: calc(64px + env(safe-area-inset-bottom, 0px));
  }
}

@media (max-width: 767px) {
  .form-card {
    padding: var(--jf-space-2);
  }

  .action-bar__buttons {
    width: 100%;
  }

  .action-bar__buttons :deep(.p-button) {
    flex: 1;
  }
}
</style>
