import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { attachmentsApi } from '@/api/attachments'
import type { Attachment, AttachmentCreate } from '@/types/api'

export const useAttachmentsStore = defineStore('attachments', () => {
  // State
  const attachments = ref<Attachment[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const getAttachmentsByMember = computed(() => {
    return (memberId: number) => {
      return attachments.value.filter(
        a => a.object_id === memberId
      )
    }
  })

  const attachmentCount = computed(() => attachments.value.length)

  // Actions
  async function fetchAttachmentsForMember(memberId: number) {
    loading.value = true
    error.value = null
    try {
      const response = await attachmentsApi.getForMember(memberId)
      attachments.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Fehler beim Laden der Anhänge'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createAttachment(formData: FormData) {
    loading.value = true
    error.value = null
    try {
      const response = await attachmentsApi.create(formData)
      attachments.value.unshift(response.data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Fehler beim Hochladen'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteAttachment(id: number) {
    loading.value = true
    error.value = null
    try {
      await attachmentsApi.delete(id)
      attachments.value = attachments.value.filter(a => a.id !== id)
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Fehler beim Löschen'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function downloadAttachment(id: number) {
    try {
      const response = await attachmentsApi.download(id)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Fehler beim Herunterladen'
      throw err
    }
  }

  function clearAttachments() {
    attachments.value = []
    error.value = null
  }

  return {
    // State
    attachments,
    loading,
    error,
    
    // Getters
    getAttachmentsByMember,
    attachmentCount,
    
    // Actions
    fetchAttachmentsForMember,
    createAttachment,
    deleteAttachment,
    downloadAttachment,
    clearAttachments
  }
})
