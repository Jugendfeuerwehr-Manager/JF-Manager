<template>
  <div class="member-edit">
    <StateView v-if="loading" kind="loading" title="Mitglied wird geladen …" />

    <template v-else>
      <nav aria-label="Brotkrumen" class="breadcrumb">
        <router-link to="/members">Mitglieder</router-link>
        <i class="pi pi-angle-right" aria-hidden="true"></i>
        <template v-if="isEditMode">
          <router-link :to="`/members/${memberId}`">{{ displayName }}</router-link>
          <i class="pi pi-angle-right" aria-hidden="true"></i>
          <span aria-current="page">Bearbeiten</span>
        </template>
        <span v-else aria-current="page">Neu</span>
      </nav>

      <header class="edit-head">
        <PrivateAvatar
          :image="avatarPreview || formData.avatar_url"
          :label="avatarPreview || formData.avatar_url ? undefined : initials"
          shape="circle"
          class="edit-head__avatar"
        />
        <div class="edit-head__text">
          <h1>{{ isEditMode ? 'Mitglied bearbeiten' : 'Mitglied anlegen' }}</h1>
          <div class="edit-head__badges">
            <MemberStatusBadge v-if="selectedStatus" :status="selectedStatus" />
            <StatusBadge v-if="isDirty" severity="warning" icon="pi pi-pencil" label="Ungespeicherte Änderungen" />
          </div>
        </div>
      </header>

      <div class="edit-layout">
        <nav class="section-nav" aria-label="Abschnitte">
          <p class="section-nav__title">Abschnitte</p>
          <a
            v-for="section in sections"
            :key="section.id"
            :href="`#${section.id}`"
            class="section-nav__link"
            :class="{ 'section-nav__link--active': activeSection === section.id }"
            @click.prevent="goToSection(section.id)"
          >
            {{ section.label }}
            <span v-if="section.errors" class="section-nav__errors" :aria-label="`${section.errors} Fehler`">{{ section.errors }}</span>
          </a>
        </nav>

        <form id="member-form" class="edit-form" novalidate @submit.prevent="handleSubmit">
          <section id="section-master" class="form-card" aria-labelledby="section-master-title">
            <h2 id="section-master-title" tabindex="-1">Stammdaten</h2>
            <div class="form-grid">
              <div class="field">
                <label for="name">Vorname</label>
                <InputText
                  id="name"
                  v-model="formData.name"
                  :invalid="!!errors.name"
                  :aria-invalid="!!errors.name || undefined"
                  :aria-describedby="errors.name ? 'name-error' : undefined"
                  autocomplete="off"
                  required
                />
                <p v-if="errors.name" id="name-error" class="field__error"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors.name }}</p>
              </div>

              <div class="field">
                <label for="lastname">Nachname</label>
                <InputText
                  id="lastname"
                  v-model="formData.lastname"
                  :invalid="!!errors.lastname"
                  :aria-invalid="!!errors.lastname || undefined"
                  :aria-describedby="errors.lastname ? 'lastname-error' : undefined"
                  autocomplete="off"
                  required
                />
                <p v-if="errors.lastname" id="lastname-error" class="field__error"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors.lastname }}</p>
              </div>

              <div class="field">
                <label for="birthday">Geburtsdatum <span class="field__optional">(TT.MM.JJJJ)</span></label>
                <Calendar
                  input-id="birthday"
                  :model-value="formData.birthday"
                  date-format="dd.mm.yy"
                  :show-icon="true"
                  :max-date="new Date()"
                  update-model-type="date"
                  :invalid="!!errors.birthday"
                  @update:model-value="(val: Date | Date[] | (Date | null)[] | null | undefined) => onDatePick('birthday', val)"
                  @input="(e: Event) => onDateTextInput('birthday', e)"
                  @blur="(e: { value: string }) => commitDateField('birthday', e.value)"
                />
                <p v-if="errors.birthday" class="field__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors.birthday }}</p>
              </div>

              <div class="field">
                <label for="gender">Geschlecht</label>
                <Select
                  input-id="gender"
                  v-model="formData.gender"
                  placeholder="Keine Angabe"
                  :options="genderOptions"
                  option-label="label"
                  option-value="value"
                />
              </div>

              <div class="field">
                <label for="identityCardNumber">Ausweisnummer <span class="field__optional">(optional)</span></label>
                <InputText id="identityCardNumber" v-model="formData.identityCardNumber" />
              </div>

              <div class="field field--check">
                <Checkbox input-id="canSwimm" v-model="formData.canSwimm" :binary="true" />
                <label for="canSwimm">Kann schwimmen</label>
              </div>
            </div>
          </section>

          <section id="section-contact" class="form-card" aria-labelledby="section-contact-title">
            <h2 id="section-contact-title" tabindex="-1">Kontakt</h2>
            <div class="form-grid">
              <div class="field">
                <label for="email">E-Mail <span class="field__optional">(optional)</span></label>
                <InputText id="email" v-model="formData.email" type="email" autocomplete="off" />
              </div>
              <div class="field">
                <label for="phone">Telefon <span class="field__optional">(optional)</span></label>
                <InputText id="phone" v-model="formData.phone" type="tel" autocomplete="off" />
              </div>
              <div class="field">
                <label for="mobile">Mobiltelefon <span class="field__optional">(optional)</span></label>
                <InputText id="mobile" v-model="formData.mobile" type="tel" autocomplete="off" />
              </div>
              <div class="field field--wide">
                <label for="street">Straße und Hausnummer</label>
                <InputText id="street" v-model="formData.street" autocomplete="off" />
              </div>
              <div class="field">
                <label for="zip_code">PLZ</label>
                <InputText id="zip_code" v-model="formData.zip_code" inputmode="numeric" autocomplete="off" />
              </div>
              <div class="field">
                <label for="city">Ort</label>
                <InputText id="city" v-model="formData.city" autocomplete="off" />
              </div>
            </div>
          </section>

          <section v-if="isEditMode" id="section-parents" class="form-card" aria-labelledby="section-parents-title">
            <div class="form-card__header">
              <h2 id="section-parents-title" tabindex="-1">Erziehungsberechtigte</h2>
              <router-link to="/parents/create" class="secondary-link"><i class="pi pi-plus" aria-hidden="true"></i>Kontakt anlegen</router-link>
            </div>
            <ul v-if="memberParents.length" class="parent-list">
              <li v-for="parent in memberParents" :key="parent.id" class="parent">
                <span class="parent__text">
                  <span class="parent__name">{{ parent.full_name }}</span>
                  <span class="parent__meta">{{ reachableNumber(parent) || 'Keine Telefonnummer' }}{{ parent.email ? ` · ${parent.email}` : '' }}</span>
                </span>
                <StatusBadge v-if="reachableNumber(parent)" severity="success" label="Erreichbar" />
                <StatusBadge v-else severity="warning" label="Notfallnummer fehlt" />
                <router-link :to="`/parents/${parent.id}/edit`" class="icon-link" :aria-label="`${parent.full_name} bearbeiten`">
                  <i class="pi pi-pencil" aria-hidden="true"></i>
                </router-link>
              </li>
            </ul>
            <p v-else class="hint">Noch keine Erziehungsberechtigten verknüpft. Kontakte werden beim Elternteil dem Mitglied zugeordnet.</p>
          </section>

          <section id="section-membership" class="form-card" aria-labelledby="section-membership-title">
            <h2 id="section-membership-title" tabindex="-1">Mitgliedschaft</h2>
            <div class="form-grid">
              <div class="field">
                <template v-if="canChangeDepartments">
                  <label for="departments">Abteilungen</label>
                  <MultiSelect
                    input-id="departments"
                    v-model="formData.departments"
                    :options="departmentOptions"
                    option-label="label"
                    option-value="value"
                    placeholder="Abteilungen auswählen"
                    display="chip"
                    :loading="departmentsStore.loading"
                  />
                </template>
                <template v-else>
                  <span id="departments-label" class="field__label">Abteilungen</span>
                  <p class="locked-value" aria-labelledby="departments-label">
                    <i class="pi pi-lock" aria-hidden="true"></i>{{ departmentNames || '–' }}
                  </p>
                  <p class="hint">Abteilungen ändert die Organisationsverwaltung.</p>
                </template>
              </div>

              <div class="field">
                <label for="group">Gruppe</label>
                <Select
                  input-id="group"
                  v-model="formData.group"
                  :options="groupOptions"
                  option-label="label"
                  option-value="value"
                  placeholder="Keine Gruppe"
                  show-clear
                  :loading="membersStore.loading"
                />
              </div>

              <div class="field">
                <label for="joined">Eintrittsdatum <span class="field__optional">(TT.MM.JJJJ)</span></label>
                <Calendar
                  input-id="joined"
                  :model-value="formData.joined"
                  date-format="dd.mm.yy"
                  :show-icon="true"
                  :max-date="new Date()"
                  update-model-type="date"
                  :invalid="!!errors.joined"
                  @update:model-value="(val: Date | Date[] | (Date | null)[] | null | undefined) => onDatePick('joined', val)"
                  @input="(e: Event) => onDateTextInput('joined', e)"
                  @blur="(e: { value: string }) => commitDateField('joined', e.value)"
                />
                <p v-if="errors.joined" class="field__error" role="alert"><i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errors.joined }}</p>
              </div>
            </div>

            <fieldset v-if="statusOptions.length" class="choice-group">
              <legend>Status</legend>
              <div class="choice-group__options">
                <label
                  v-for="option in statusOptions"
                  :key="option.value"
                  class="choice"
                  :class="{ 'choice--selected': formData.status === option.value }"
                >
                  <input v-model="formData.status" type="radio" name="status" :value="option.value" />
                  {{ option.label }}
                </label>
              </div>
            </fieldset>
          </section>

          <section id="section-notes" class="form-card" aria-labelledby="section-notes-title">
            <h2 id="section-notes-title" tabindex="-1">Hinweise</h2>
            <div class="field">
              <label for="notes">Bemerkungen</label>
              <Textarea id="notes" v-model="formData.notes" rows="4" auto-resize aria-describedby="notes-hint" />
              <p id="notes-hint" class="hint">Sichtbar für alle, die dieses Mitglied ansehen dürfen. In der Detailansicht erst auf Abruf eingeblendet.</p>
            </div>
          </section>

          <section id="section-photo" class="form-card" aria-labelledby="section-photo-title">
            <h2 id="section-photo-title" tabindex="-1">Profilbild</h2>
            <div class="avatar-upload">
              <div v-if="avatarPreview || formData.avatar_url" class="avatar-preview">
                <Image
                  :src="(avatarPreview || formData.avatar_url) as string"
                  alt="Profilbild"
                  width="150"
                  preview
                />
                <Button
                  icon="pi pi-times"
                  rounded
                  text
                  severity="danger"
                  aria-label="Profilbild entfernen"
                  class="remove-avatar"
                  type="button"
                  @click="removeAvatar"
                />
              </div>
              <div v-if="avatarPreview" class="avatar-controls">
                <Button
                  icon="pi pi-undo"
                  label="Nach links drehen"
                  severity="secondary"
                  outlined
                  type="button"
                  @click="rotateAvatar(-90)"
                  :disabled="saving"
                />
                <Button
                  icon="pi pi-refresh"
                  label="Nach rechts drehen"
                  severity="secondary"
                  outlined
                  type="button"
                  @click="rotateAvatar(90)"
                  :disabled="saving"
                />
              </div>
              <div class="avatar-controls">
                <FileUpload
                  mode="basic"
                  accept="image/*"
                  :maxFileSize="5000000"
                  :auto="false"
                  chooseLabel="Bild auswählen"
                  @select="onFileSelect"
                  :disabled="saving"
                />
                <Button
                  icon="pi pi-camera"
                  label="Kamera öffnen"
                  severity="secondary"
                  outlined
                  type="button"
                  @click="openCamera"
                  :disabled="saving"
                />
              </div>
            </div>
          </section>
        </form>
      </div>

      <div class="action-bar">
        <p class="action-bar__status" :class="{ 'action-bar__status--error': errorCount, 'action-bar__status--idle': !errorCount && !isDirty }" role="status">
          <template v-if="errorCount">
            <i class="pi pi-exclamation-circle" aria-hidden="true"></i>{{ errorCount === 1 ? '1 Feld braucht' : `${errorCount} Felder brauchen` }} deine Aufmerksamkeit
          </template>
          <template v-else-if="isDirty">
            <i class="pi pi-pencil" aria-hidden="true"></i>Ungespeicherte Änderungen
          </template>
          <template v-else-if="isEditMode">
            <i class="pi pi-check" aria-hidden="true"></i>Keine Änderungen
          </template>
        </p>
        <div class="action-bar__buttons">
          <Button label="Abbrechen" severity="secondary" text type="button" :disabled="saving" @click="cancel" />
          <Button
            :label="isEditMode ? 'Änderungen speichern' : 'Mitglied anlegen'"
            icon="pi pi-check"
            type="submit"
            form="member-form"
            :loading="saving"
          />
        </div>
      </div>
    </template>

    <Dialog
      v-model:visible="cameraVisible"
      modal
      header="Profilbild aufnehmen"
      :style="{ width: 'min(32rem, 95vw)' }"
      @hide="closeCamera"
    >
      <div class="camera-dialog">
        <template v-if="cameraPermissionPending">
          <p>Für die Aufnahme wird Zugriff auf Ihre Kamera benötigt.</p>
          <div class="camera-actions">
            <Button label="Abbrechen" severity="secondary" type="button" @click="closeCamera" />
            <Button label="Kamera erlauben" icon="pi pi-camera" type="button" @click="requestCameraPermission" />
          </div>
        </template>
        <template v-else>
          <video ref="cameraVideo" autoplay playsinline class="camera-video" />
          <small v-if="cameraError" class="p-error">{{ cameraError }}</small>
          <Button
            label="Aufnehmen"
            icon="pi pi-camera"
            type="button"
            :disabled="!!cameraError"
            @click="capturePhoto"
          />
        </template>
      </div>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useMembersStore } from '@/stores/members'
import { useDepartmentsStore } from '@/stores/departments'
import { useAuthStore } from '@/stores/auth'
import type { Parent } from '@/types/parents'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Calendar from 'primevue/calendar'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import FileUpload from 'primevue/fileupload'
import Image from '@/components/common/PrivateImage.vue'
import PrivateAvatar from '@/components/common/PrivateAvatar.vue'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import MemberStatusBadge from '@/components/members/atoms/MemberStatusBadge.vue'
import Dialog from 'primevue/dialog'
import { getApiErrorMessage } from '@/utils/apiError'
import { parseFlexibleDate, formatDateGerman } from '@/utils/dateParsing'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const membersStore = useMembersStore()
const departmentsStore = useDepartmentsStore()
const authStore = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const isEditMode = computed(() => !!route.params.id)
const memberId = computed(() => Number(route.params.id))
const memberParents = ref<Parent[]>([])
const activeSection = ref('section-master')
/** Serialised form state right after loading; compared to detect unsaved changes. */
const savedSnapshot = ref('')
const avatarFile = ref<File | null>(null)
const avatarPreview = ref<string | null>(null)
const cameraVisible = ref(false)
const cameraPermissionPending = ref(false)
const cameraError = ref('')
const cameraVideo = ref<HTMLVideoElement | null>(null)
let cameraStream: MediaStream | null = null

const genderOptions = [
  { label: 'Keine Angabe', value: '' },
  { label: 'Männlich', value: 'male' },
  { label: 'Weiblich', value: 'female' },
  { label: 'Divers', value: 'diverse' }
]

const formData = reactive({
  name: '',
  lastname: '',
  birthday: null as Date | null,
  gender: '' as string,
  email: '',
  street: '',
  zip_code: '',
  city: '',
  phone: '',
  mobile: '',
  notes: '',
  joined: null as Date | null,
  identityCardNumber: '',
  canSwimm: false,
  status: null as number | null,
  group: null as number | null,
  storage_location: null as number | null,
  avatar_url: null as string | null,
  departments: [] as number[],
})

const errors = reactive({
  name: '',
  lastname: '',
  birthday: '',
  joined: ''
})

// Raw text the user is currently typing into the date fields, used to validate on blur/submit
const birthdayText = ref('')
const joinedText = ref('')

const statusOptions = computed(() => membersStore.statusOptions)
const groupOptions = computed(() => membersStore.groupOptions)
const departmentOptions = computed(() =>
  departmentsStore.departments.map((d) => ({ label: `${d.name} (${d.code})`, value: d.id })),
)

/** Department assignments of existing members are changed by organisation-wide administrators only. */
const canChangeDepartments = computed(() => !isEditMode.value || authStore.isOrgWide)
const departmentNames = computed(() => formData.departments
  .map((id) => departmentsStore.departments.find((d) => d.id === id))
  .map((d) => (d ? `${d.code} · ${d.name}` : ''))
  .filter(Boolean)
  .join(', '))

const displayName = computed(() => [formData.name, formData.lastname].filter(Boolean).join(' ') || 'Mitglied')
const initials = computed(() => `${formData.name[0] ?? ''}${formData.lastname[0] ?? ''}`.toUpperCase())
const selectedStatus = computed(() => membersStore.statuses.find((status) => status.id === formData.status) ?? null)
const reachableNumber = (parent: Parent) => parent.mobile || parent.phone || ''

const snapshot = () => JSON.stringify({ ...formData, birthday: birthdayText.value, joined: joinedText.value })
const isDirty = computed(() => !!avatarFile.value || (savedSnapshot.value !== '' && snapshot() !== savedSnapshot.value))

const sections = computed(() => [
  { id: 'section-master', label: 'Stammdaten', errors: [errors.name, errors.lastname, errors.birthday].filter(Boolean).length },
  { id: 'section-contact', label: 'Kontakt', errors: 0 },
  ...(isEditMode.value ? [{ id: 'section-parents', label: 'Erziehungsberechtigte', errors: 0 }] : []),
  { id: 'section-membership', label: 'Mitgliedschaft', errors: errors.joined ? 1 : 0 },
  { id: 'section-notes', label: 'Hinweise', errors: 0 },
  { id: 'section-photo', label: 'Profilbild', errors: 0 },
])
const errorCount = computed(() => sections.value.reduce((sum, section) => sum + section.errors, 0))

function goToSection(id: string) {
  activeSection.value = id
  const section = document.getElementById(id)
  section?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  document.getElementById(`${id}-title`)?.focus({ preventScroll: true })
}

function focusFirstError() {
  const firstInvalid = ['name', 'lastname', 'birthday', 'joined'].find((field) => errors[field as keyof typeof errors])
  if (!firstInvalid) return
  const input = document.getElementById(firstInvalid)
  input?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  input?.focus({ preventScroll: true })
}

function cancel() {
  router.push(isEditMode.value ? `/members/${memberId.value}` : '/members')
}

onMounted(async () => {
  // Load statuses, groups and departments
  await Promise.all([
    membersStore.fetchStatuses(),
    membersStore.fetchGroups(),
    departmentsStore.departments.length === 0 ? departmentsStore.fetchDepartments() : Promise.resolve(),
  ])

  // If editing, load member data
  if (isEditMode.value) {
    loading.value = true
    try {
      const member = await membersStore.fetchMemberById(Number(route.params.id))
      Object.assign(formData, {
        name: member.name,
        lastname: member.lastname,
        birthday: member.birthday ? new Date(member.birthday) : null,
        gender: member.gender || '',
        email: member.email,
        street: member.street,
        zip_code: member.zip_code,
        city: member.city,
        phone: member.phone,
        mobile: member.mobile,
        notes: member.notes ?? '',
        joined: member.joined ? new Date(member.joined) : null,
        identityCardNumber: member.identityCardNumber,
        canSwimm: member.canSwimm,
        status: member.status?.id || null,
        group: member.group?.id || null,
        storage_location: member.storage_location,
        avatar_url: member.avatar_url,
        departments: member.department_ids ?? [],
      })
      memberParents.value = member.parents ?? []

      const groupStillAvailable =
        formData.group === null || membersStore.groups.some((group) => group.id === formData.group)
      if (!groupStillAvailable) {
        formData.group = null
      }

      birthdayText.value = formatDateGerman(formData.birthday)
      joinedText.value = formatDateGerman(formData.joined)
    } catch {
      toast.add({
        severity: 'error',
        summary: 'Fehler',
        detail: 'Mitglied konnte nicht geladen werden',
        life: 3000
      })
      router.push('/members')
    } finally {
      loading.value = false
    }
  }
  savedSnapshot.value = snapshot()
})

type DateField = 'birthday' | 'joined'

const dateFieldTexts: Record<DateField, typeof birthdayText> = {
  birthday: birthdayText,
  joined: joinedText,
}

// Calendar popup selection always yields a valid Date (or null when cleared)
function onDatePick(field: DateField, value: unknown) {
  const date = value instanceof Date ? value : null
  formData[field] = date
  dateFieldTexts[field].value = formatDateGerman(date)
  errors[field] = ''
}

function onDateTextInput(field: DateField, event: Event) {
  dateFieldTexts[field].value = (event.target as HTMLInputElement).value
}

// Parses the raw typed text and commits it to formData, or sets a validation error
function commitDateField(field: DateField, rawText: string): boolean {
  const trimmed = rawText.trim()
  if (!trimmed) {
    formData[field] = null
    errors[field] = ''
    return true
  }

  const parsed = parseFlexibleDate(trimmed)
  if (!parsed) {
    errors[field] = 'Ungültiges Datum. Bitte z.B. TT.MM.JJJJ eingeben.'
    return false
  }
  if (parsed > new Date()) {
    errors[field] = 'Datum darf nicht in der Zukunft liegen.'
    return false
  }

  formData[field] = parsed
  dateFieldTexts[field].value = formatDateGerman(parsed)
  errors[field] = ''
  return true
}

function onFileSelect(event: { files: File[] }) {
  const file = event.files[0]
  if (file) {
    avatarFile.value = file
    const reader = new FileReader()
    reader.onload = (e) => {
      avatarPreview.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }
}

function openCamera() {
  cameraError.value = ''
  cameraVisible.value = true
  cameraPermissionPending.value = true
}

async function requestCameraPermission() {
  cameraPermissionPending.value = false
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraError.value = 'Die Kamera wird von diesem Browser nicht unterstützt.'
    return
  }

  await nextTick()
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
    if (cameraVideo.value) {
      cameraVideo.value.srcObject = cameraStream
    }
  } catch {
    cameraError.value = 'Kamerazugriff nicht möglich. Bitte prüfen Sie die Browser-Berechtigung.'
  }
}

function closeCamera() {
  cameraStream?.getTracks().forEach((track) => track.stop())
  cameraStream = null
  cameraPermissionPending.value = false
  if (cameraVideo.value) {
    cameraVideo.value.srcObject = null
  }
  cameraVisible.value = false
}

function capturePhoto() {
  const video = cameraVideo.value
  if (!video || video.videoWidth === 0 || video.videoHeight === 0) return

  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d')?.drawImage(video, 0, 0)
  canvas.toBlob((blob) => {
    if (!blob) return
    const file = new File([blob], `member-avatar-${Date.now()}.jpg`, { type: 'image/jpeg' })
    avatarFile.value = file
    avatarPreview.value = URL.createObjectURL(file)
    closeCamera()
  }, 'image/jpeg', 0.92)
}

async function rotateAvatar(degrees: number) {
  if (!avatarPreview.value) return
  const image = new window.Image()
  image.src = avatarPreview.value
  await new Promise<void>((resolve, reject) => {
    image.onload = () => resolve()
    image.onerror = () => reject(new Error('Bild konnte nicht geladen werden'))
  })

  const canvas = document.createElement('canvas')
  const quarterTurn = Math.abs(degrees) % 180 === 90
  canvas.width = quarterTurn ? image.height : image.width
  canvas.height = quarterTurn ? image.width : image.height
  const context = canvas.getContext('2d')
  if (!context) return
  context.translate(canvas.width / 2, canvas.height / 2)
  context.rotate((degrees * Math.PI) / 180)
  context.drawImage(image, -image.width / 2, -image.height / 2)
  canvas.toBlob((blob) => {
    if (!blob) return
    const file = new File([blob], `member-avatar-${Date.now()}.jpg`, { type: 'image/jpeg' })
    avatarFile.value = file
    avatarPreview.value = URL.createObjectURL(file)
  }, 'image/jpeg', 0.92)
}

function removeAvatar() {
  avatarFile.value = null
  avatarPreview.value = null
  formData.avatar_url = null
}

function validateForm(): boolean {
  let isValid = true
  errors.name = ''
  errors.lastname = ''

  if (!formData.name.trim()) {
    errors.name = 'Vorname ist erforderlich'
    isValid = false
  }

  if (!formData.lastname.trim()) {
    errors.lastname = 'Nachname ist erforderlich'
    isValid = false
  }

  if (!commitDateField('birthday', birthdayText.value)) {
    isValid = false
  }

  if (!commitDateField('joined', joinedText.value)) {
    isValid = false
  }

  return isValid
}

async function handleSubmit() {
  if (!validateForm()) {
    toast.add({
      severity: 'warn',
      summary: 'Validierung fehlgeschlagen',
      detail: 'Bitte korrigieren Sie die markierten Felder',
      life: 3000
    })
    await nextTick()
    focusFirstError()
    return
  }

  saving.value = true

  try {
    const formDataToSend = new FormData()
    
    // Add all fields to FormData
    formDataToSend.append('name', formData.name)
    formDataToSend.append('lastname', formData.lastname)
    
    if (formData.birthday) {
      const birthdayStr = formData.birthday.toISOString().split('T')[0]
      if (birthdayStr) {
        formDataToSend.append('birthday', birthdayStr)
      }
    }
    if (formData.email) formDataToSend.append('email', formData.email)
    if (formData.street) formDataToSend.append('street', formData.street)
    if (formData.zip_code) formDataToSend.append('zip_code', formData.zip_code)
    if (formData.city) formDataToSend.append('city', formData.city)
    if (formData.phone) formDataToSend.append('phone', formData.phone)
    if (formData.mobile) formDataToSend.append('mobile', formData.mobile)
    formDataToSend.append('notes', formData.notes)
    if (formData.joined) {
      const joinedStr = formData.joined.toISOString().split('T')[0]
      if (joinedStr) {
        formDataToSend.append('joined', joinedStr)
      }
    }
    if (formData.identityCardNumber) formDataToSend.append('identityCardNumber', formData.identityCardNumber)
    if (formData.gender) formDataToSend.append('gender', formData.gender)
    formDataToSend.append('canSwimm', String(formData.canSwimm))
    
    if (formData.status !== null) formDataToSend.append('status', String(formData.status))
    if (formData.group !== null) formDataToSend.append('group', String(formData.group))
    if (formData.storage_location !== null) formDataToSend.append('storage_location', String(formData.storage_location))

    // M2M departments — append each ID as a separate entry; omitted when locked so they stay unchanged
    if (canChangeDepartments.value) {
      for (const deptId of formData.departments) {
        formDataToSend.append('departments', String(deptId))
      }
    }

    if (avatarFile.value) {
      formDataToSend.append('avatar', avatarFile.value)
    }

    if (isEditMode.value) {
      await membersStore.updateMember(Number(route.params.id), formDataToSend)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Mitglied wurde aktualisiert',
        life: 3000
      })
    } else {
      await membersStore.createMember(formDataToSend)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Mitglied wurde erstellt',
        life: 3000
      })
    }

    savedSnapshot.value = snapshot()
    avatarFile.value = null
    router.push(isEditMode.value ? `/members/${memberId.value}` : '/members')
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: getApiErrorMessage(error, 'Ein Fehler ist aufgetreten'),
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(closeCamera)
</script>

<style scoped>
.member-edit {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
  max-width: 1200px;
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

.breadcrumb a {
  color: var(--jf-color-primary);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.breadcrumb i {
  font-size: 0.75rem;
}

.edit-head {
  display: flex;
  align-items: center;
  gap: var(--jf-space-2);
}

.edit-head__avatar {
  flex: none;
  width: 56px;
  height: 56px;
  background: var(--surface-hover);
  color: var(--p-surface-700);
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-bold);
}

.app-dark .edit-head__avatar {
  color: var(--p-surface-200);
}

.edit-head__text {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  min-width: 0;
}

.edit-head h1 {
  margin: 0;
  font-size: var(--jf-text-2xl);
  line-height: var(--jf-leading-tight);
  letter-spacing: -0.015em;
}

.edit-head__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
}

.edit-layout {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--jf-space-3);
}

.section-nav {
  position: sticky;
  top: calc(var(--topbar-height, 64px) + var(--jf-space-3));
  flex: 1 1 200px;
  max-width: 240px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.section-nav__title {
  margin: 0 var(--jf-space-1-5) var(--jf-space-1);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--jf-color-text-muted);
}

.section-nav__link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-medium);
  text-decoration: none;
}

.section-nav__link:hover {
  background: var(--surface-hover);
}

.section-nav__link--active {
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
  font-weight: var(--jf-weight-semibold);
}

.section-nav__errors {
  display: inline-grid;
  place-items: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--p-red-100);
  color: var(--p-red-800);
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
}

.app-dark .section-nav__errors {
  background: color-mix(in srgb, var(--p-red-400), transparent 84%);
  color: var(--p-red-300);
}

.edit-form {
  flex: 999 1 520px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-3);
}

.form-card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-3);
  padding: var(--jf-space-3);
  background: var(--jf-color-card);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  box-shadow: var(--jf-shadow-sm);
  scroll-margin-top: calc(var(--topbar-height, 64px) + var(--jf-space-2));
}

.form-card h2 {
  margin: 0;
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-semibold);
}

.form-card h2:focus {
  outline: none;
}

.form-card__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1-5);
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

.field label,
.field__label {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-text);
}

.field__optional {
  font-weight: 400;
  color: var(--jf-color-text-muted);
}

.field--check {
  flex-direction: row;
  align-items: center;
  align-self: end;
  gap: var(--jf-space-1-5);
  min-height: var(--jf-touch-target);
}

.field :deep(.p-inputtext),
.field :deep(.p-select),
.field :deep(.p-multiselect),
.field :deep(.p-datepicker),
.field :deep(.p-textarea) {
  width: 100%;
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

.hint {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
}

.locked-value {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  margin: 0;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-ground);
  color: var(--jf-color-text);
  font-size: var(--jf-text-sm);
}

.locked-value i {
  color: var(--jf-color-text-muted);
}

.choice-group {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
  padding: 0;
  border: 0;
}

.choice-group legend {
  margin-bottom: var(--jf-space-1);
  padding: 0;
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
}

.choice-group__options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
}

.choice {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 14px;
  border: 1px solid var(--p-surface-300);
  border-radius: var(--jf-radius-md);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-medium);
  cursor: pointer;
}

.choice input {
  width: 18px;
  height: 18px;
  margin: 0;
  accent-color: var(--jf-color-primary);
}

.choice--selected {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
  font-weight: var(--jf-weight-semibold);
}

.choice:has(input:focus-visible) {
  outline: var(--jf-focus-ring);
  outline-offset: 2px;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target);
  padding: 0 var(--jf-space-2);
  border: 1px solid var(--p-surface-300);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-semibold);
  text-decoration: none;
}

.parent-list {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.parent {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.parent__text {
  flex: 1 1 200px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.parent__name {
  font-weight: var(--jf-weight-semibold);
}

.parent__meta {
  font-size: 0.8125rem;
  color: var(--jf-color-text-muted);
  overflow-wrap: anywhere;
}

.icon-link {
  display: inline-grid;
  place-items: center;
  width: var(--jf-touch-target);
  height: var(--jf-touch-target);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text-muted);
  text-decoration: none;
}

.icon-link:hover {
  background: var(--surface-hover);
  color: var(--jf-color-text);
}

.avatar-upload {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.avatar-controls {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1-5);
}

.avatar-preview {
  position: relative;
  align-self: flex-start;
}

.remove-avatar {
  position: absolute;
  top: -0.5rem;
  right: -0.5rem;
}

.camera-dialog {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.camera-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}

.camera-video {
  width: 100%;
  max-height: 60vh;
  object-fit: contain;
  background: #000;
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
  margin: 0 calc(-1 * var(--jf-space-4)) calc(-1 * var(--jf-space-3));
  padding: var(--jf-space-1-5) var(--jf-space-4);
  background: var(--jf-color-card);
  border-top: 1px solid var(--jf-color-border);
  box-shadow: 0 -4px 12px rgba(23, 32, 51, 0.06);
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

@media (max-width: 1023px) {
  .section-nav {
    display: none;
  }

  .action-bar {
    bottom: calc(64px + env(safe-area-inset-bottom, 0px));
    margin: 0 calc(-1 * var(--jf-space-2));
    padding: var(--jf-space-1) var(--jf-space-2);
  }
}

@media (max-width: 767px) {
  .form-card {
    padding: var(--jf-space-2);
    gap: var(--jf-space-2);
  }

  .edit-head h1 {
    font-size: var(--jf-text-xl);
  }

  .action-bar__status {
    flex: 1 1 100%;
  }

  .action-bar__status--idle {
    display: none;
  }

  .action-bar__buttons {
    flex: 1 1 100%;
  }

  .action-bar__buttons :deep(.p-button:last-child) {
    flex: 1;
  }
}

@media (max-width: 480px) {
  .action-bar {
    margin: 0 calc(-1 * var(--jf-space-1-5));
    padding: var(--jf-space-1) var(--jf-space-1-5);
  }
}
</style>
