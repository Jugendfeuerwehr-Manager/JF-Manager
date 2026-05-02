<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import { useMembersStore } from '@/stores/members'
import { useUsersStore } from '@/stores/users'
import type { QualificationCreate, QualificationUpdate, Qualification } from '@/types/qualifications'
import Card from 'primevue/card'
import Calendar from 'primevue/calendar'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import InputNumber from 'primevue/inputnumber'
import InputSwitch from 'primevue/inputswitch'
import SelectButton from 'primevue/selectbutton'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  qualificationId?: number
  initialData?: Qualification
  defaultMemberId?: number  // Pre-set member when creating from member profile
}

const props = defineProps<Props>()

const emit = defineEmits<{
  success: [qualificationId: number]
  cancel: []
}>()

const qualificationsStore = useQualificationsStore()
const membersStore = useMembersStore()
const usersStore = useUsersStore()

// Form state
const formData = ref<QualificationCreate>({
  type: 0,
  member: null,
  user: null,
  date_acquired: '',
  date_expires: null,
  issued_by: '',
  note: ''
})

const loading = ref(false)
const error = ref<string | null>(null)
const isEditMode = computed(() => !!props.qualificationId || !!props.initialData)

// Validity period in months (not from backend, calculated manually)
const validityMonths = ref<number | null>(null)
const assignmentTarget = ref<'member' | 'user'>('member')
const assignmentOptions = [
  { label: 'Mitglied', value: 'member' as const },
  { label: 'Benutzer', value: 'user' as const }
]
const autoCalculateExpiry = ref(true)

// Helper function to convert ISO date string to Date object
function toISODateString(date: Date): string {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

// Computed properties for date fields (Calendar expects Date objects)
const dateAcquiredModel = computed<Date | null>({
  get() {
    return formData.value.date_acquired ? new Date(formData.value.date_acquired) : null
  },
  set(value) {
    formData.value.date_acquired = value ? toISODateString(value) : ''
  }
})

const dateExpiresModel = computed<Date | null>({
  get() {
    return formData.value.date_expires ? new Date(formData.value.date_expires) : null
  },
  set(value) {
    formData.value.date_expires = value ? toISODateString(value) : null
  }
})

// Load initial data if editing
onMounted(async () => {
  // Load qualification types, members and users
  await Promise.all([
    qualificationsStore.fetchQualificationTypes(),
    membersStore.fetchMembers({ limit: 1000 }),
    usersStore.fetchUsers({ limit: 1000, is_active: true })
  ])

  // Priority 1: Load by ID (most reliable - fetches from API)
  if (props.qualificationId) {
    const qualification = await qualificationsStore.fetchQualification(props.qualificationId)
    if (qualification) {
      formData.value = {
        type: qualification.type,
        member: qualification.member,
        user: qualification.user,
        date_acquired: qualification.date_acquired,
        date_expires: qualification.date_expires,
        issued_by: qualification.issued_by,
        note: qualification.note
      }
      // Determine assignment target based on which field has a valid ID
      assignmentTarget.value = (qualification.member !== null && qualification.member !== undefined && qualification.member > 0) ? 'member' : 'user'
      autoCalculateExpiry.value = !!qualificationsStore.qualificationTypes.find(t => t.id === qualification.type)?.expires
      
      // Calculate validity months
      if (qualification.date_acquired && qualification.date_expires) {
        const acquired = new Date(qualification.date_acquired)
        const expires = new Date(qualification.date_expires)
        const monthsDiff = (expires.getFullYear() - acquired.getFullYear()) * 12 + 
                          (expires.getMonth() - acquired.getMonth())
        validityMonths.value = monthsDiff
      }
    }
  }
  // Priority 2: Use initialData (for backward compatibility, but less preferred)
  else if (props.initialData) {
    // Edit mode: load existing qualification data
    formData.value = {
      type: props.initialData.type,
      member: props.initialData.member,
      user: props.initialData.user,
      date_acquired: props.initialData.date_acquired,
      date_expires: props.initialData.date_expires,
      issued_by: props.initialData.issued_by,
      note: props.initialData.note
    }
    // Determine assignment target based on which field has a valid ID
    assignmentTarget.value = (props.initialData.member !== null && props.initialData.member !== undefined && props.initialData.member > 0) ? 'member' : 'user'
    autoCalculateExpiry.value = !!qualificationsStore.qualificationTypes.find(t => t.id === props.initialData!.type)?.expires
    
    // Calculate validity months if dates are present
    if (props.initialData.date_acquired && props.initialData.date_expires) {
      const acquired = new Date(props.initialData.date_acquired)
      const expires = new Date(props.initialData.date_expires)
      const monthsDiff = (expires.getFullYear() - acquired.getFullYear()) * 12 + 
                        (expires.getMonth() - acquired.getMonth())
      validityMonths.value = monthsDiff
    }
  }
  // Priority 3: New qualification - pre-set member if creating from member profile
  else if (props.defaultMemberId) {
    formData.value.member = props.defaultMemberId
    assignmentTarget.value = 'member'
    autoCalculateExpiry.value = false
  }

  recalculateExpiry()
})

// Computed properties for dropdowns
const qualificationTypeOptions = computed(() => 
  qualificationsStore.qualificationTypes.map(type => ({
    label: `${type.name} [G]`,
    value: type.id
  }))
)

const memberOptions = computed(() => 
  membersStore.members.map(member => ({
    label: member.full_name,
    value: member.id
  }))
)

const userOptions = computed(() => 
  usersStore.users.map(user => ({
    label: user.full_name || user.username,
    value: user.id
  }))
)

const selectedType = computed(() => 
  qualificationsStore.qualificationTypes.find(t => t.id === formData.value.type)
)

// Handle type changes and auto-calculation defaults
watch(
  () => formData.value.type,
  (newTypeId) => {
    const type = qualificationsStore.qualificationTypes.find(t => t.id === newTypeId)
    if (type?.expires) {
      autoCalculateExpiry.value = true
      if (type.validity_period) {
        validityMonths.value = type.validity_period
      }
      recalculateExpiry()
    } else {
      autoCalculateExpiry.value = false
      validityMonths.value = null
      formData.value.date_expires = null
      recalculateExpiry()
    }
  }
)

// Ensure XOR between member and user selection (but not during initialization)
watch(assignmentTarget, (target, oldTarget) => {
  // Only clear fields if this is an actual user-initiated change, not during setup
  if (oldTarget === undefined) {
    return // Skip first initialization
  }
  
  if (target === 'member') {
    formData.value.user = null
  } else {
    formData.value.member = null
  }
})

// Helper to recalculate expiry date when auto mode is active
function recalculateExpiry() {
  if (!autoCalculateExpiry.value) {
    return
  }

  const dateAcquired = formData.value.date_acquired
  const months = validityMonths.value

  if (dateAcquired && months && months > 0) {
    const acquired = new Date(dateAcquired)
    const expires = new Date(acquired)
    expires.setMonth(expires.getMonth() + months)
    formData.value.date_expires = expires.toISOString().split('T')[0]
  } else {
    formData.value.date_expires = null
  }
}

// Recalculate when dependencies change
watch(
  [() => formData.value.date_acquired, () => validityMonths.value, () => autoCalculateExpiry.value],
  () => {
    recalculateExpiry()
  }
)

// Form validation
function normalizeDateValue(value: string | null | undefined): string | null {
  if (!value) return null
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

const hasAssignee = computed(() => {
  if (assignmentTarget.value === 'member') {
    return formData.value.member !== null && formData.value.member !== undefined && formData.value.member > 0
  }
  return formData.value.user !== null && formData.value.user !== undefined && formData.value.user > 0
})

const isFormValid = computed(() => {
  return formData.value.type > 0 &&
         hasAssignee.value &&
         !!formData.value.date_acquired
})

// Submit handler
const handleSubmit = async () => {
  if (!isFormValid.value) {
    error.value = 'Bitte füllen Sie alle Pflichtfelder aus.'
    return
  }

  loading.value = true
  error.value = null

  try {
    if (isEditMode.value && (props.qualificationId || props.initialData?.id)) {
      const id = props.qualificationId || props.initialData!.id
      const updateData: QualificationUpdate = {
        ...formData.value,
        member: assignmentTarget.value === 'member' ? formData.value.member : null,
        user: assignmentTarget.value === 'user' ? formData.value.user : null,
        date_expires: normalizeDateValue(formData.value.date_expires)
      }
      await qualificationsStore.updateQualification(id, updateData)
      emit('success', id)
    } else {
      const createData: QualificationCreate = {
        ...formData.value,
        member: assignmentTarget.value === 'member' ? formData.value.member : null,
        user: assignmentTarget.value === 'user' ? formData.value.user : null,
        date_expires: normalizeDateValue(formData.value.date_expires)
      }
      const newQualification = await qualificationsStore.createQualification(createData)
      emit('success', newQualification.id)
    }
  } catch (err) {
    error.value = getApiErrorMessage(err, 'Fehler beim Speichern der Qualifikation')
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  emit('cancel')
}
</script>

<template>
  <Card>
    <template #title>
      {{ isEditMode ? 'Qualifikation bearbeiten' : 'Neue Qualifikation' }}
    </template>
    <template #content>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div v-if="qualificationsStore.loading || membersStore.loading" class="flex justify-center py-8">
        <ProgressSpinner />
      </div>

      <form v-else @submit.prevent="handleSubmit" class="qualification-form">
        <!-- Row 1: Qualification Type and Assignment Target -->
        <div class="form-row">
          <div class="form-field">
            <label for="type" class="font-semibold">Qualifikationstyp *</label>
            <Dropdown
              id="type"
              v-model="formData.type"
              :options="qualificationTypeOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Qualifikationstyp auswählen"
              :disabled="loading"
              class="w-full"
            />
            <small v-if="selectedType?.description" class="text-gray-600">
              {{ selectedType.description }}
            </small>
          </div>

          <div class="form-field">
            <label class="font-semibold">Zuweisung *</label>
            <SelectButton
              v-model="assignmentTarget"
              :options="assignmentOptions"
              optionLabel="label"
              optionValue="value"
              :disabled="loading"
              class="assignment-toggle"
            />
            <small class="text-gray-600">
              Entscheide, ob die Qualifikation einem Mitglied oder einem Benutzer zugeordnet wird.
            </small>
          </div>
        </div>

        <!-- Row 2: Person/User Selection -->
        <div class="form-row">
          <div class="form-field form-field-full">
            <label :for="assignmentTarget === 'member' ? 'member' : 'user'" class="font-semibold">
              {{ assignmentTarget === 'member' ? 'Mitglied' : 'Benutzer' }} *
            </label>

            <Dropdown
              v-if="assignmentTarget === 'member'"
              id="member"
              v-model="formData.member"
              :options="memberOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Mitglied auswählen"
              :disabled="loading"
              filter
              showClear
              class="w-full"
            />

            <Dropdown
              v-else
              id="user"
              v-model="formData.user"
              :options="userOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Benutzer auswählen"
              :disabled="loading"
              filter
              showClear
              class="w-full"
            />
          </div>
        </div>

        <!-- Row 2: Date Acquired and Validity -->
        <div class="form-row">
          <div class="form-field">
            <label for="date_acquired" class="font-semibold">Erwerbsdatum *</label>
            <Calendar
              id="date_acquired"
              v-model="dateAcquiredModel"
              dateFormat="dd.mm.yy"
              placeholder="TT.MM.JJJJ"
              :disabled="loading"
              showIcon
              updateModelType="date"
              class="w-full"
            />
          </div>

          <div class="form-field">
            <label for="validity_months" class="font-semibold">Gültigkeit (Monate)</label>
            <InputNumber
              id="validity_months"
              v-model="validityMonths"
              placeholder="z.B. 24 für 2 Jahre"
              :disabled="loading"
              :min="0"
              :max="120"
              class="w-full"
              suffix=" Monate"
            />
            <small class="text-gray-600">
              Leer lassen für unbegrenzte Gültigkeit
            </small>
          </div>
        </div>

        <!-- Row 3: Expiry Date and Issuer -->
          <div class="form-field">
            <div class="field-label">
              <label for="date_expires" class="font-semibold">Ablaufdatum</label>
              <div class="auto-switch" :class="{ disabled: !selectedType?.expires }">
                <InputSwitch v-model="autoCalculateExpiry" :disabled="!selectedType?.expires" />
                <span>Automatisch</span>
              </div>
            </div>
            <Calendar
              id="date_expires"
              v-model="dateExpiresModel"
              dateFormat="dd.mm.yy"
              placeholder="TT.MM.JJJJ"
              :disabled="autoCalculateExpiry && !!selectedType?.expires"
              showIcon
              updateModelType="date"
              class="w-full"
            />
            />
            <small class="text-gray-600">
              <span v-if="selectedType?.expires">
                Schalte die automatische Berechnung aus, um ein individuelles Ablaufdatum zu setzen.
              </span>
              <span v-else>
                Optionales Ablaufdatum festlegen.
              </span>
            </small>
          </div>

          <div class="form-field">
            <label for="issued_by" class="font-semibold">Ausgestellt von</label>
            <InputText
              id="issued_by"
              v-model="formData.issued_by"
              placeholder="z.B. Landesfeuerwehrverband"
              :disabled="loading"
              class="w-full"
            />
          </div>
     

        <!-- Row 4: Notes (full width) -->
        <div class="form-row">
          <div class="form-field form-field-full">
            <label for="note" class="font-semibold">Notizen</label>
            <Textarea
              id="note"
              v-model="formData.note"
              rows="3"
              placeholder="Zusätzliche Informationen..."
              :disabled="loading"
              class="w-full"
            />
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-2 justify-end mt-4">
          <Button
            label="Abbrechen"
            severity="secondary"
            @click="handleCancel"
            :disabled="loading"
          />
          <Button
            type="submit"
            :label="isEditMode ? 'Aktualisieren' : 'Erstellen'"
            :loading="loading"
            :disabled="!isFormValid"
          />
        </div>
      </form>
    </template>
  </Card>
</template>

<style scoped>
.qualification-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-field-full {
  grid-column: 1 / -1;
}

.assignment-toggle {
  width: 100%;
}

.assignment-toggle :deep(.p-button) {
  flex: 1;
}

.field-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.auto-switch {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.auto-switch.disabled {
  opacity: 0.6;
}

/* Responsive: Stack fields vertically on mobile */
@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
}
</style>
