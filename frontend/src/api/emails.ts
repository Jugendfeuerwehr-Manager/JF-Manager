/**
 * API client for email messaging system
 */

import apiClient from './index'
import type {
  EmailMessage,
  EmailMessageDetail,
  EmailMessageCreate,
  EmailTemplateVariable,
  EmailPreviewRequest,
  EmailPreviewResponse,
  EmailSendResponse,
  EmailRecipientCountRequest,
  EmailRecipientCountResponse,
  EmailListParams,
  PaginatedResponse
} from '@/types/emails'

export const emailsApi = {
  /**
   * List all emails with optional filters
   */
  list(params?: EmailListParams) {
    return apiClient.get<PaginatedResponse<EmailMessage>>('/emails/', { params })
  },

  /**
   * Get a single email by ID
   */
  get(id: number) {
    return apiClient.get<EmailMessageDetail>(`/emails/${id}/`)
  },

  /**
   * Create and send an email
   */
  send(data: EmailMessageCreate) {
    return apiClient.post<EmailSendResponse>('/emails/send/', data)
  },

  /**
   * Resend failed recipients for an email
   */
  resend(id: number) {
    return apiClient.post<EmailSendResponse>(`/emails/${id}/resend/`)
  },

  /**
   * Preview an email with template rendering
   */
  preview(data: EmailPreviewRequest) {
    return apiClient.post<EmailPreviewResponse>('/emails/preview/', data)
  },

  /**
   * Get available template variables
   */
  getTemplateVariables() {
    return apiClient.get<EmailTemplateVariable[]>('/emails/template_variables/')
  },

  /**
   * Get recipient count for selection criteria
   */
  getRecipientCount(data: EmailRecipientCountRequest) {
    return apiClient.post<EmailRecipientCountResponse>('/emails/recipient_count/', data)
  }
}
