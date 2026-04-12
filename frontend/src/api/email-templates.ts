/**
 * API Client for Email Templates
 * Handles CRUD operations and template preview
 */

import apiClient from './index'
import type {
  EmailTemplateList,
  EmailTemplate,
  EmailTemplateCreateUpdate,
  TemplateType,
  AllTemplateVariables,
  TemplateVariables,
  TemplatePreviewRequest,
  TemplatePreviewResponse
} from '@/types/email-templates'
import type { PaginatedResponse } from '@/types/orders'

export const emailTemplatesApi = {
  /**
   * List all email templates
   */
  list() {
    return apiClient.get<PaginatedResponse<EmailTemplateList>>('/settings/email-templates/')
  },

  /**
   * Get email template details
   */
  get(id: number) {
    return apiClient.get<EmailTemplate>(`/settings/email-templates/${id}/`)
  },

  /**
   * Create new email template
   */
  create(data: EmailTemplateCreateUpdate) {
    return apiClient.post<EmailTemplate>('/settings/email-templates/', data)
  },

  /**
   * Update existing email template
   */
  update(id: number, data: EmailTemplateCreateUpdate) {
    return apiClient.put<EmailTemplate>(`/settings/email-templates/${id}/`, data)
  },

  /**
   * Partially update email template
   */
  patch(id: number, data: Partial<EmailTemplateCreateUpdate>) {
    return apiClient.patch<EmailTemplate>(`/settings/email-templates/${id}/`, data)
  },

  /**
   * Delete email template
   */
  delete(id: number) {
    return apiClient.delete(`/settings/email-templates/${id}/`)
  },

  /**
   * Get available template types
   */
  getTypes() {
    return apiClient.get<TemplateType[]>('/settings/email-templates/types/')
  },

  /**
   * Get template variables for all types or specific type
   */
  getVariables(templateType?: string) {
    const params = templateType ? { template_type: templateType } : undefined
    return apiClient.get<AllTemplateVariables | (TemplateVariables & { template_type: string })>(
      '/settings/email-templates/variables/',
      { params }
    )
  },

  /**
   * Preview template with sample data
   */
  preview(data: TemplatePreviewRequest) {
    return apiClient.post<TemplatePreviewResponse>('/settings/email-templates/preview/', data)
  },

  /**
   * Get default template content from files
   */
  getDefaultContent(templateType: string) {
    return apiClient.get<{
      template_type: string
      subject_template: string
      html_template: string
      text_template: string
    }>('/settings/email-templates/default_content/', {
      params: { template_type: templateType }
    })
  }
}
