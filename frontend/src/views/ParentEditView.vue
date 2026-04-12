<template>
  <div class="parent-edit-view">
    <div class="header">
      <Button 
        icon="pi pi-arrow-left" 
        text 
        rounded 
        @click="router.push('/parents')"
        aria-label="Zurück"
      />
      <h1>{{ isEditMode ? 'Elternteil bearbeiten' : 'Neuer Elternteil' }}</h1>
    </div>

    <Card v-if="!loading || formData">
      <template #content>
        <form @submit.prevent="handleSubmit" class="parent-form">
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
            </div>
          </Panel>

          <!-- Contact Information -->
          <Panel header="Kontaktdaten" :toggleable="true" class="panel mt-3">
            <div class="form-grid">
              <div class="field">
                <label for="email">E-Mail *</label>
                <InputText 
                  id="email" 
                  v-model="formData.email" 
                  type="email"
                  :invalid="!!errors.email"
                  required
                />
                <small v-if="errors.email" class="p-error">{{ errors.email }}</small>
              </div>

              <div class="field">
                <label for="email2">E-Mail 2</label>
                <InputText 
                  id="email2" 
                  v-model="formData.email2" 
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

          <!-- Children Selection -->
          <Panel header="Kinder" :toggleable="true" class="panel mt-3">
            <div class="form-grid">
              <div class="field col-12">
                <label for="children">Zugeordnete Mitglieder</label>
                <MultiSelect 
                  id="children" 
                  v-model="formData.children" 
                  :options="memberOptions"
                  optionLabel="label"
                  optionValue="value"
                  placeholder="Mitglieder auswählen"
                  :loading="membersStore.loading"
                  filter
                  :maxSelectedLabels="3"
                />
              </div>
            </div>
          </Panel>

          <!-- Notes -->
          <Panel header="Notizen" :toggleable="true" class="panel mt-3">
            <div class="form-grid">
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

          <!-- Action Buttons -->
          <div class="form-actions">
            <Button 
              label="Abbrechen" 
              icon="pi pi-times" 
              severity="secondary"
              @click="router.push('/parents')"
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
import { useParentsStore } from '@/stores/parents'
import { useMembersStore } from '@/stores/members'
import Card from 'primevue/card'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import MultiSelect from 'primevue/multiselect'
import ProgressSpinner from 'primevue/progressspinner'
import { getApiErrorMessage } from '@/utils/apiError'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const parentsStore = useParentsStore()
const membersStore = useMembersStore()

const loading = ref(false)
const saving = ref(false)
const isEditMode = computed(() => !!route.params.id)

const formData = reactive({
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
  children: [] as number[]
})

const errors = reactive({
  name: '',
  lastname: '',
  email: ''
})

const memberOptions = computed(() => membersStore.memberOptions)

onMounted(async () => {
  // Load members for selection
  await membersStore.fetchMembers({ limit: 1000 })

  // If editing, load parent data
  if (isEditMode.value) {
    loading.value = true
    try {
      const parent = await parentsStore.fetchParentById(Number(route.params.id))
      Object.assign(formData, {
        name: parent.name,
        lastname: parent.lastname,
        email: parent.email,
        email2: parent.email2,
        phone: parent.phone,
        mobile: parent.mobile,
        street: parent.street,
        zip_code: parent.zip_code,
        city: parent.city,
        notes: parent.notes,
        children: parent.children || []
      })
    } catch {
      toast.add({
        severity: 'error',
        summary: 'Fehler',
        detail: 'Elternteil konnte nicht geladen werden',
        life: 3000
      })
      router.push('/parents')
    } finally {
      loading.value = false
    }
  }
})

function validateForm(): boolean {
  let isValid = true
  errors.name = ''
  errors.lastname = ''
  errors.email = ''

  if (!formData.name.trim()) {
    errors.name = 'Vorname ist erforderlich'
    isValid = false
  }

  if (!formData.lastname.trim()) {
    errors.lastname = 'Nachname ist erforderlich'
    isValid = false
  }

  if (!formData.email.trim()) {
    errors.email = 'E-Mail ist erforderlich'
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
    const dataToSend = { ...formData }

    if (isEditMode.value) {
      await parentsStore.updateParent(Number(route.params.id), dataToSend)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Elternteil wurde aktualisiert',
        life: 3000
      })
    } else {
      await parentsStore.createParent(dataToSend)
      toast.add({
        severity: 'success',
        summary: 'Erfolg',
        detail: 'Elternteil wurde erstellt',
        life: 3000
      })
    }

    router.push('/parents')
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
</script>

<style scoped>

.panel {
  margin-bottom: 1.5rem;
}

.parent-edit-view {
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

.parent-form {
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

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
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
