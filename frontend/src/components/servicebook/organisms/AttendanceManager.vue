<template>
  <div class="attendance-manager">
    <div class="manager-header">
      <IconField iconPosition="left">
        <InputIcon>
          <i class="pi pi-search" />
        </InputIcon>
        <InputText
          v-model="searchQuery"
          placeholder="Mitglied suchen..."
          class="search-input"
        />
      </IconField>
    </div>

    <Divider />

    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <ProgressSpinner />
    </div>

    <!-- Member List -->
    <div v-else class="members-list">
      <div
        v-for="member in filteredMembers"
        :key="member.id"
        class="member-item"
      >
        <div class="member-info">
          <span class="member-name">{{ member.full_name }}</span>
        </div>
        <AttendanceButtonGroup
          :current-state="getAttendanceState(member.id)"
          :loading="updatingMemberId === member.id"
          @select="(state) => handleAttendanceUpdate(member.id, state)"
        />
      </div>

      <!-- Empty State -->
      <div v-if="filteredMembers.length === 0" class="empty-state">
        <p>Keine Mitglieder gefunden</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'primevue/usetoast'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Button from 'primevue/button'
import Divider from 'primevue/divider'
import ProgressSpinner from 'primevue/progressspinner'
import AttendanceButtonGroup from '../atoms/AttendanceButtonGroup.vue'
import type { AttendanceState } from '@/types/servicebook'
import { useMembersStore } from '@/stores/members'
import { useServicebookStore } from '@/stores/servicebook'

interface Props {
  serviceId: number
}

const props = defineProps<Props>()

const toast = useToast()
const membersStore = useMembersStore()
const servicebookStore = useServicebookStore()

const searchQuery = ref('')
const updatingMemberId = ref<number | null>(null)

// Local attendance state
const localAttendance = ref<Map<number, AttendanceState | null>>(new Map())
const initialAttendance = ref<Map<number, AttendanceState | null>>(new Map())

// Computed loading state
const loading = computed(() => membersStore.loading)

// Load members and initialize attendance on mount
onMounted(async () => {
  if (membersStore.members.length === 0) {
    await membersStore.fetchMembers({ limit: 1000 })
  }
  initializeAttendance()
})

// Watch for current service changes to reload attendance
watch(
  () => servicebookStore.currentService,
  (newService) => {
    if (newService && newService.id === props.serviceId) {
      initializeAttendance()
    }
  },
  { deep: true }
)

const initializeAttendance = () => {
  localAttendance.value.clear()
  initialAttendance.value.clear()

  const currentService = servicebookStore.currentService
  if (!currentService || currentService.id !== props.serviceId) return

  // Map attendees by person ID
  if (currentService.attendees_with_status) {
    currentService.attendees_with_status.forEach((attendee) => {
      localAttendance.value.set(attendee.id, attendee.state)
      initialAttendance.value.set(attendee.id, attendee.state)
    })
  }
}

const filteredMembers = computed(() => {
  const query = searchQuery.value.toLowerCase()
  if (!query) return membersStore.members

  return membersStore.members.filter((member) => {
    const fullName = `${member.name} ${member.lastname}`.toLowerCase()
    return fullName.includes(query)
  })
})

const getAttendanceState = (memberId: number): AttendanceState | null => {
  return localAttendance.value.get(memberId) || null
}

const handleAttendanceUpdate = async (memberId: number, state: AttendanceState) => {
  updatingMemberId.value = memberId
  
  // Toggle behavior: if same state clicked, clear it
  const currentState = localAttendance.value.get(memberId)
  const newState = currentState === state ? null : state
  
  // Update local state immediately for UI responsiveness
  if (newState === null) {
    localAttendance.value.delete(memberId)
  } else {
    localAttendance.value.set(memberId, newState)
  }

  // Save to server immediately
  try {
    console.log('AttendanceManager: Updating attendance for member', memberId, 'to state', newState)
    
    // Build the full attendance list from current state
    const attendances = Array.from(localAttendance.value.entries()).map(([person_id, state]) => ({
      person_id,
      state
    }))
    
    // If we're clearing this member's attendance, explicitly send null
    if (newState === null) {
      attendances.push({ person_id: memberId, state: null })
    }

    await servicebookStore.bulkUpdateAttendance({
      service: props.serviceId,
      attendances
    })
    
    // Update initial state to reflect saved state
    if (newState === null) {
      initialAttendance.value.delete(memberId)
    } else {
      initialAttendance.value.set(memberId, newState)
    }
    
    console.log('AttendanceManager: Attendance updated successfully')
  } catch (error: any) {
    console.error('AttendanceManager: Update error', error)
    
    // Revert local state on error
    if (currentState === null || currentState === undefined) {
      localAttendance.value.delete(memberId)
    } else {
      localAttendance.value.set(memberId, currentState)
    }
    
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: error.message || 'Fehler beim Speichern der Anwesenheit',
      life: 5000
    })
  } finally {
    updatingMemberId.value = null
  }
}
</script>

<style scoped>
.attendance-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface-0);
  border-radius: var(--border-radius);
  border: 1px solid var(--surface-border);
}

.manager-header {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.manager-header h3 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.search-input {
  width: 100%;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
}

.members-list {
  flex: 1;
  min-height: 0; /* Critical for flex child with overflow */
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.member-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem;
  background: var(--surface-50);
  border-radius: var(--border-radius);
}

.member-info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  flex: 1;
}

.member-name {
  font-weight: 500;
  color: var(--text-color);
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
  color: var(--text-color-secondary);
}
</style>
