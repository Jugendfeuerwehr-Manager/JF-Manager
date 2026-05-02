import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { eventsApi, eventTypesApi } from '@/api/members'
import type { Event, EventType, EventCreate } from '@/types/api'
import { getApiErrorMessage } from '@/utils/apiError'

export const useEventsStore = defineStore('events', () => {
  // State
  const events = ref<Event[]>([])
  const eventTypes = ref<EventType[]>([])
  const eventTypesDepartmentContext = ref<number | null | undefined>(undefined)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const eventTypeOptions = computed(() =>
    eventTypes.value.map(t => ({
      label: t.department === null ? `${t.name} (Global)` : t.name,
      value: t.id
    }))
  )

  const getEventsByMember = computed(() => {
    return (memberId: number) => {
      return events.value
        .filter(e => e.member === memberId)
        .sort((a, b) => new Date(b.datetime).getTime() - new Date(a.datetime).getTime())
    }
  })

  const eventCount = computed(() => events.value.length)

  // Actions
  async function fetchEventTypes() {
    const activeDepartmentRaw = localStorage.getItem('activeDepartmentId')
    const activeDepartmentId = activeDepartmentRaw ? Number(activeDepartmentRaw) : null

    if (eventTypes.value.length > 0 && eventTypesDepartmentContext.value === activeDepartmentId) {
      return eventTypes.value
    }

    try {
      const response = await eventTypesApi.list()
      eventTypes.value = response.data.results || []
      eventTypesDepartmentContext.value = activeDepartmentId
      return eventTypes.value
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Ereignistypen')
      throw err
    }
  }

  async function fetchEventsForMember(memberId: number) {
    loading.value = true
    error.value = null
    try {
      const response = await eventsApi.list({ 
        member: memberId, 
        ordering: '-datetime' 
      })
      const memberEvents = response.data.results || []
      
      // Update events array - replace existing member events
      events.value = [
        ...events.value.filter(e => e.member !== memberId),
        ...memberEvents
      ]
      
      return memberEvents
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Laden der Einträge')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createEvent(eventData: EventCreate) {
    loading.value = true
    error.value = null
    try {
      // Prepare data in the format expected by the API
      const apiData: Omit<Event, 'id' | 'member_name' | 'event_type'> = {
        member: eventData.member,
        type: eventData.type,
        datetime: eventData.datetime,
        notes: eventData.notes || ''
      }
      const response = await eventsApi.create(apiData)
      events.value.unshift(response.data)
      return response.data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Erstellen')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateEvent(id: number, eventData: Partial<EventCreate>) {
    loading.value = true
    error.value = null
    try {
      // Prepare data in the format expected by the API
      const apiData: Partial<Omit<Event, 'id' | 'member_name' | 'event_type'>> = {
        ...(eventData.member !== undefined && { member: eventData.member }),
        ...(eventData.type !== undefined && { type: eventData.type }),
        ...(eventData.datetime !== undefined && { datetime: eventData.datetime }),
        ...(eventData.notes !== undefined && { notes: eventData.notes || '' })
      }
      const response = await eventsApi.update(id, apiData)
      const index = events.value.findIndex(e => e.id === id)
      if (index !== -1) {
        events.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Aktualisieren')
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteEvent(id: number) {
    loading.value = true
    error.value = null
    try {
      await eventsApi.delete(id)
      events.value = events.value.filter(e => e.id !== id)
    } catch (err) {
      error.value = getApiErrorMessage(err, 'Fehler beim Löschen')
      throw err
    } finally {
      loading.value = false
    }
  }

  function clearEvents() {
    events.value = []
    eventTypes.value = []
    eventTypesDepartmentContext.value = undefined
    error.value = null
  }

  return {
    // State
    events,
    eventTypes,
    loading,
    error,
    
    // Getters
    eventTypeOptions,
    getEventsByMember,
    eventCount,
    
    // Actions
    fetchEventTypes,
    fetchEventsForMember,
    createEvent,
    updateEvent,
    deleteEvent,
    clearEvents
  }
})
