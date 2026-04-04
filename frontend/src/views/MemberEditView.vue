<template>
  <div class="member-edit-view">
    <div class="header">
      <Button 
        icon="pi pi-arrow-left" 
        text 
        rounded 
        @click="router.push('/members')"
        aria-label="Zurück"
      />
      <h1>{{ isEditMode ? 'Mitglied bearbeiten' : 'Neues Mitglied' }}</h1>
    </div>

    <Card v-if="!loading || formData">
      <template #content>
        <form @submit.prevent="handleSubmit" class="member-form">
          <!-- Basic Information -->
          <Panel header="Persönliche Daten" :toggleable="true" class="panel">
            <div class="form-grid">
              <div class="field">
                <label for="name">Vorname *</label>
                <InputText 
                  id="name" 
                  v-model="formData.name" 
                  :invalid="!!errors.name"
                  required
                />
                <small v-if="errors.name" class="p-error">{{ errors.name }}</small>
              </div>

              <div class="field">
                <label for="lastname">Nachname *</label>
                <InputText 
                  id="lastname" 
                  v-model="formData.lastname" 
                  :invalid="!!errors.lastname"
                  required
                />
                <small v-if="errors.lastname" class="p-error">{{ errors.lastname }}</small>
              </div>

              <div class="field">
                <label for="birthday">Geburtsdatum</label>
                <Calendar 
                  id="birthday" 
                  v-model="formData.birthday" 
                  date-format="yy-mm-dd"
                  :show-icon="true"
                  :max-date="new Date()"
                  update-model-type="replace"
                />
              </div>

              <div class="field">
                <label for="identityCardNumber">Ausweisnummer</label>
                <InputText 
                  id="identityCardNumber" 
                  v-model="formData.identityCardNumber" 
                />
              </div>

              <div class="field">
                <label for="email">E-Mail</label>
                <InputText 
                  id="email" 
                  v-model="formData.email" 
                  type="email"
                />
              </div>

              <div class="field">
                <label for="phone">Telefon</label>
                <InputText 
                  id="phone" 
                  v-model="formData.phone" 
                />
              </div>

              <div class="field">
                <label for="mobile">Mobiltelefon</label>
                <InputText 
                  id="mobile" 
                  v-model="formData.mobile" 
                />
              </div>

              <div class="field col-12">
                <label>Geschlecht</label>
                <SelectButton
                  v-model="formData.gender"
                  :options="genderOptions"
                  option-label="label"
                  option-value="value"
                  class="gender-select-button"
                />
              </div>

              <div class="field field-checkbox">
                <Checkbox 
                  id="canSwimm" 
                  v-model="formData.canSwimm" 
                  :binary="true"
                />
                <label for="canSwimm">Kann schwimmen</label>
              </div>
            </div>
          </Panel>

          <!-- Address Information -->
          <Panel header="Adresse" :toggleable="true" class="panel mt-3">
            <div class="form-grid">
              <div class="field col-12">
                <label for="street">Straße</label>
                <InputText 
                  id="street" 
                  v-model="formData.street" 
                />
              </div>

              <div class="field">
                <label for="zip_code">PLZ</label>
                <InputText 
                  id="zip_code" 
                  v-model="formData.zip_code" 
                />
              </div>

              <div class="field">
                <label for="city">Stadt</label>
                <InputText 
                  id="city" 
                  v-model="formData.city" 
                />
              </div>
            </div>
          </Panel>

          <!-- Member Information -->
          <Panel header="Mitgliedschaft" :toggleable="true" class="panel mt-3">
            <div class="form-grid">
              <div class="field">
                <label for="joined">Eintrittsdatum</label>
                <Calendar 
                  id="joined" 
                  v-model="formData.joined" 
                  date-format="yy-mm-dd"
                  :show-icon="true"
                  :max-date="new Date()"
                  update-model-type="replace"
                />
              </div>

              <div class="field">
                <label for="status">Status</label>
                <Dropdown 
                  id="status" 
                  v-model="formData.status" 
                  :options="statusOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Status auswählen"
                  :loading="membersStore.loading"
                />
              </div>

              <div class="field">
                <label for="group">Gruppe</label>
                <Dropdown 
                  id="group" 
                  v-model="formData.group" 
                  :options="groupOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Gruppe auswählen"
                  :loading="membersStore.loading"
                />
              </div>

              <div class="field col-12">
                <label for="notes">Notizen</label>
                <Textarea 
                  id="notes" 
                  v-model="formData.notes" 
                  rows="4"
                  autoResize
                />
              </div>
            </div>
          </Panel>

          <!-- Avatar Upload -->
          <Panel header="Profilbild" :toggleable="true" class="panel mt-3">
            <div class="avatar-upload">
              <div v-if="avatarPreview || formData.avatar_url" class="avatar-preview">
                <Image 
                  :src="(avatarPreview || formData.avatar_url) as string" 
                  alt="Avatar" 
                  width="150"
                  preview
                />
                <Button 
                  icon="pi pi-times" 
                  rounded 
                  text 
                  severity="danger"
                  @click="removeAvatar"
                  class="remove-avatar"
                />
              </div>
              <FileUpload
                mode="basic"
                accept="image/*"
                :maxFileSize="5000000"
                :auto="false"
                chooseLabel="Bild auswählen"
                @select="onFileSelect"
                :disabled="saving"
              />
            </div>
          </Panel>

          <!-- Action Buttons -->
          <div class="form-actions">
            <Button 
              label="Abbrechen" 
              icon="pi pi-times" 
              severity="secondary"
              @click="router.push('/members')"
              :disabled="saving"
            />
            <Button 
              label="Speichern" 
              icon="pi pi-check" 
              type="submit"
              :loading="saving"
            />
          </div>
        </form>
      </template>
    </Card>

    <div v-else class="loading-container">
      <ProgressSpinner />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useMembersStore } from '@/stores/members'
import Card from 'primevue/card'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Calendar from 'primevue/calendar'
import Dropdown from 'primevue/dropdown'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import SelectButton from 'primevue/selectbutton'
import FileUpload from 'primevue/fileupload'
import Image from 'primevue/image'
import ProgressSpinner from 'primevue/progressspinner'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const membersStore = useMembersStore()

const loading = ref(false)
const saving = ref(false)
const isEditMode = computed(() => !!route.params.id)
const avatarFile = ref<File | null>(null)
const avatarPreview = ref<string | null>(null)

const genderOptions = [
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
  avatar_url: null as string | null
})

const errors = reactive({
  name: '',
  lastname: ''
})

const statusOptions = computed(() => membersStore.statusOptions)
const groupOptions = computed(() => membersStore.groupOptions)

onMounted(async () => {
  // Load statuses and groups
  await Promise.all([
    membersStore.fetchStatuses(),
    membersStore.fetchGroups()
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
        notes: member.notes,
        joined: member.joined ? new Date(member.joined) : null,
        identityCardNumber: member.identityCardNumber,
        canSwimm: member.canSwimm,
        status: member.status?.id || null,
        group: member.group?.id || null,
        storage_location: member.storage_location,
        avatar_url: member.avatar_url
      })
    } catch (error) {
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
})

function onFileSelect(event: any) {
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

  return isValid
}

async function handleSubmit() {
  if (!validateForm()) {
    toast.add({
      severity: 'warn',
      summary: 'Validierung fehlgeschlagen',
      detail: 'Bitte füllen Sie alle erforderlichen Felder aus',
      life: 3000
    })
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
    if (formData.notes) formDataToSend.append('notes', formData.notes)
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

    router.push('/members')
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: error.response?.data?.detail || 'Ein Fehler ist aufgetreten',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.panel {
  margin-bottom: 1.5rem;
}
.member-edit-view {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.header h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 600;
}

.member-form {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  padding: 1rem 0;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field.col-12 {
  grid-column: 1 / -1;
}

.field label {
  font-weight: 500;
  color: var(--text-color);
}

.field-checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.75rem;
}

.field-checkbox label {
  margin: 0;
}

.gender-select-button :deep(.p-selectbutton) {
  width: 100%;
  display: flex;
}

.gender-select-button :deep(.p-togglebutton) {
  flex: 1;
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
}

.avatar-upload {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem 0;
}

.avatar-preview {
  position: relative;
  display: inline-block;
}

.remove-avatar {
  position: absolute;
  top: -0.5rem;
  right: -0.5rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid var(--surface-border);
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  
  .form-actions {
    flex-direction: column-reverse;
  }
  
  .form-actions button {
    width: 100%;
  }
}
</style>
