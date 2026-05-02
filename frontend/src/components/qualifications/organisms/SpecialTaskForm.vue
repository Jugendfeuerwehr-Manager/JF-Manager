<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useQualificationsStore } from '@/stores/qualifications'
import { useMembersStore } from '@/stores/members'
import { useUsersStore } from '@/stores/users'
import type { SpecialTaskCreate, SpecialTaskUpdate, SpecialTask } from '@/types/qualifications'
import Card from 'primevue/card'
import Calendar from 'primevue/calendar'
import Dropdown from 'primevue/dropdown'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import Textarea from 'primevue/textarea'
import SelectButton from 'primevue/selectbutton'
import { getApiErrorMessage } from '@/utils/apiError'

interface Props {
  taskId?: number
  initialData?: SpecialTask
  defaultMemberId?: number  // Pre-set member when creating from member profile
}

const props = defineProps<Props>()

const emit = defineEmits<{
  success: [taskId: number]
  cancel: []
}>()

const qualificationsStore = useQualificationsStore()
const membersStore = useMembersStore()
const usersStore = useUsersStore()

// Form state
const formData = ref<SpecialTaskCreate>({
  task: 0,
  member: null,
  user: null,
  start_date: '',
  end_date: '',
  note: ''
})

const loading = ref(false)
const error = ref<string | null>(null)
const isEditMode = computed(() => !!props.taskId || !!props.initialData)
const assignmentTarget = ref<'member' | 'user'>('member')
const assignmentOptions = [
  { label: 'Mitglied', value: 'member' as const },
  { label: 'Benutzer', value: 'user' as const }
]

// Load initial data if editing
onMounted(async () => {
  // Load special task types, members and users
  await Promise.all([
    qualificationsStore.fetchSpecialTaskTypes(),
    membersStore.fetchMembers({ limit: 1000 }),
    usersStore.fetchUsers({ limit: 1000, is_active: true })
  ])

  // Priority 1: Load by ID (most reliable - fetches from API)
  if (props.taskId) {
    const task = await qualificationsStore.fetchSpecialTask(props.taskId)
    if (task) {
      formData.value = {
        task: task.task,
        member: task.member || null,
        user: task.user || null,
        start_date: task.start_date,
        end_date: task.end_date || '',
        note: task.note || ''
      }
      // Determine assignment target based on which field has a valid ID
      assignmentTarget.value = (task.member !== null && task.member !== undefined && task.member > 0) ? 'member' : 'user'
    }
  }
  // Priority 2: Use initialData (for backward compatibility, but less preferred)
  else if (props.initialData) {
    // Edit mode: load existing special task data
    formData.value = {
      task: props.initialData.task,
      member: props.initialData.member || null,
      user: props.initialData.user || null,
      start_date: props.initialData.start_date,
      end_date: props.initialData.end_date || '',
      note: props.initialData.note || ''
    }
    // Determine assignment target based on which field has a valid ID
    assignmentTarget.value = (props.initialData.member !== null && props.initialData.member !== undefined && props.initialData.member > 0) ? 'member' : 'user'
  }
  // Priority 3: New task - pre-set member if creating from member profile
  else if (props.defaultMemberId) {
    formData.value.member = props.defaultMemberId
    assignmentTarget.value = 'member'
  }
})

// Computed properties for dropdowns
const specialTaskTypeOptions = computed(() => 
  qualificationsStore.specialTaskTypes.map(type => ({
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
  qualificationsStore.specialTaskTypes.find(t => t.id === formData.value.task)
)

const hasAssignee = computed(() => {
  if (assignmentTarget.value === 'member') {
    return formData.value.member !== null && formData.value.member !== undefined && formData.value.member > 0
  }
  return formData.value.user !== null && formData.value.user !== undefined && formData.value.user > 0
})

function toISODateString(date: Date): string {
  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const startDateModel = computed<Date | null>({
  get() {
    return formData.value.start_date ? new Date(formData.value.start_date) : null
  },
  set(value) {
    formData.value.start_date = value ? toISODateString(value) : ''
  }
})

const endDateModel = computed<Date | null>({
  get() {
    return formData.value.end_date ? new Date(formData.value.end_date) : null
  },
  set(value) {
    formData.value.end_date = value ? toISODateString(value) : ''
  }
})

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

// Form validation
const isFormValid = computed(() => {
  return formData.value.task > 0 &&
         hasAssignee.value &&
         formData.value.start_date.length > 0
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
    if (isEditMode.value && (props.taskId || props.initialData?.id)) {
      const id = props.taskId || props.initialData!.id
      const updateData: SpecialTaskUpdate = {
        task: formData.value.task,
        start_date: formData.value.start_date,
        end_date: formData.value.end_date || null,  // Send null instead of empty string
        note: formData.value.note,
        // Only send the selected assignment type (don't send null for the other)
        ...(assignmentTarget.value === 'member' 
          ? { member: formData.value.member }
          : { user: formData.value.user }
        )
      }
      await qualificationsStore.updateSpecialTask(id, updateData)
      emit('success', id)
    } else {
      const createData: SpecialTaskCreate = {
        task: formData.value.task,
        start_date: formData.value.start_date,
        end_date: formData.value.end_date || null,  // Send null instead of empty string
        note: formData.value.note,
        // Only send the selected assignment type (don't send null for the other)
        ...(assignmentTarget.value === 'member' 
          ? { member: formData.value.member }
          : { user: formData.value.user }
        )
      }
      const newTask = await qualificationsStore.createSpecialTask(createData)
      emit('success', newTask.id)
    }
  } catch (err) {
    // Handle field-specific validation errors from backend
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const anyErr = err as any
    if (anyErr.response?.data) {
      const errorData = anyErr.response.data
      // Check for field-specific errors (e.g., {"task": ["Invalid pk"]})
      if (typeof errorData === 'object' && !errorData.detail) {
        const fieldErrors = Object.entries(errorData)
          .map(([field, messages]) => {
            const fieldLabel = {
              task: 'Sonderaufgabe',
              member: 'Mitglied',
              user: 'Benutzer',
              start_date: 'Startdatum',
              end_date: 'Enddatum'
            }[field] || field
            return `${fieldLabel}: ${Array.isArray(messages) ? messages.join(', ') : messages}`
          })
          .join('\n')
        error.value = fieldErrors
      } else {
        error.value = getApiErrorMessage(err, 'Fehler beim Speichern der Sonderaufgabe')
      }
    } else {
      error.value = getApiErrorMessage(err, 'Fehler beim Speichern der Sonderaufgabe')
    }
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
      {{ isEditMode ? 'Sonderaufgabe bearbeiten' : 'Neue Sonderaufgabe' }}
    </template>
    <template #content>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <div v-if="qualificationsStore.loading || membersStore.loading" class="flex justify-center py-8">
        <ProgressSpinner />
      </div>

      <form v-else @submit.prevent="handleSubmit" class="task-form">
        <div class="form-row">
          <div class="form-field">
            <label for="task" class="font-semibold">Aufgabentyp *</label>
            <Dropdown
              id="task"
              v-model="formData.task"
              :options="specialTaskTypeOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Aufgabentyp auswählen"
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
              Entscheide, ob die Sonderaufgabe einem Mitglied oder Benutzer zugeordnet wird.
            </small>
          </div>
        </div>

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

        <div class="form-row">
          <div class="form-field">
            <label for="start_date" class="font-semibold">Startdatum *</label>
            <Calendar
              id="start_date"
              v-model="startDateModel"
              updateModelType="date"
              dateFormat="dd.mm.yy"
              placeholder="TT.MM.JJJJ"
              :disabled="loading"
              showIcon
              class="w-full"
            />
          </div>
          <div class="form-field">
            <Calendar
              id="end_date"
              v-model="endDateModel"
              updateModelType="date"
              dateFormat="dd.mm.yy"
              placeholder="TT.MM.JJJJ (optional)"
              :disabled="loading"
              showIcon
              class="w-full"
            />
            <small class="text-gray-600">
              Leer lassen für laufende Aufgaben
            </small>
          </div>
        </div>

        <div class="form-row">
          <div class="form-field form-field-full">
            <label for="note" class="font-semibold">Notizen</label>
            <Textarea
              id="note"
              v-model="formData.note"
              rows="3"
              autoResize
              placeholder="Zusätzliche Hinweise..."
              :disabled="loading"
              class="w-full"
            />
          </div>
        </div>

        <div class="form-actions">
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
.task-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
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

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

@media (max-width: 768px) {
  .task-form {
    gap: 1.25rem;
  }

  .form-row {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .form-actions {
    flex-direction: column-reverse;
  }

  .form-actions :deep(.p-button) {
    width: 100%;
    justify-content: center;
  }
}
</style>
