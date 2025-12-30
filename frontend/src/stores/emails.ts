/**
 * Pinia store for email messaging system
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { emailsApi } from '@/api/emails'
import type {
  EmailMessage,
  EmailMessageDetail,
  EmailMessageCreate,
  EmailTemplateVariable,
  EmailPreviewRequest,
  EmailListParams,
  EmailRecipientCountRequest
} from '@/types/emails'

export const useEmailsStore = defineStore('emails', () => {
  // State
  const emails = ref<EmailMessage[]>([])
  const currentEmail = ref<EmailMessageDetail | null>(null)
  const templateVariables = ref<EmailTemplateVariable[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    count: 0,
    next: null as string | null,
    previous: null as string | null
  })

  // Computed
  const hasEmails = computed(() => emails.value.length > 0)

  // Actions
  async function fetchEmails(params?: EmailListParams) {
    loading.value = true
    error.value = null

    try {
      const response = await emailsApi.list(params)
      emails.value = response.data.results
      pagination.value = {
        count: response.data.count,
        next: response.data.next,
        previous: response.data.previous
      }
      return emails.value
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Fehler beim Laden der E-Mails'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchEmailById(id: number) {
    loading.value = true
    error.value = null

    try {
      const response = await emailsApi.get(id)
      currentEmail.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Fehler beim Laden der E-Mail'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function sendEmail(data: EmailMessageCreate) {
    loading.value = true
    error.value = null

    try {
      const response = await emailsApi.send(data)
      emails.value.unshift(response.data.email)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Fehler beim Senden der E-Mail'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function resendEmail(id: number) {
    loading.value = true
    error.value = null

    try {
      const response = await emailsApi.resend(id)
      
      // Update email in list
      const index = emails.value.findIndex(e => e.id === id)
      if (index !== -1) {
        emails.value[index] = response.data.email
      }
      
      // Update current email if viewing
      if (currentEmail.value?.id === id) {
        currentEmail.value = response.data.email
      }
      
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Fehler beim erneuten Senden'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function previewEmail(data: EmailPreviewRequest) {
    loading.value = true
    error.value = null

    try {
      const response = await emailsApi.preview(data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Fehler bei der Vorschau'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchTemplateVariables() {
    if (templateVariables.value.length > 0) {
      return templateVariables.value
    }

    loading.value = true
    error.value = null

    try {
      const response = await emailsApi.getTemplateVariables()
      templateVariables.value = response.data
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Fehler beim Laden der Variablen'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getRecipientCount(data: EmailRecipientCountRequest) {
    loading.value = true
    error.value = null

    try {
      const response = await emailsApi.getRecipientCount(data)
      return response.data
    } catch (err: any) {
      error.value = err.response?.data?.error || 'Fehler beim Berechnen der Empfänger'
      throw err
    } finally {
      loading.value = false
    }
  }

  function resetStore() {
    emails.value = []
    currentEmail.value = null
    templateVariables.value = []
    error.value = null
    pagination.value = {
      count: 0,
      next: null,
      previous: null
    }
  }

  return {
    // State
    emails,
    currentEmail,
    templateVariables,
    loading,
    error,
    pagination,
    // Computed
    hasEmails,
    // Actions
    fetchEmails,
    fetchEmailById,
    sendEmail,
    resendEmail,
    previewEmail,
    fetchTemplateVariables,
    getRecipientCount,
    resetStore
  }
})
