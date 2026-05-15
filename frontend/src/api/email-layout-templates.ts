import apiClient from './index'
import type { EmailLayoutTemplate, EmailLayoutTemplateUpdate } from '@/types/email-layout-templates'

export const emailLayoutTemplatesApi = {
  list() {
    return apiClient.get<EmailLayoutTemplate[]>('/settings/email-layout-templates/')
  },
  get(layoutType: string) {
    return apiClient.get<EmailLayoutTemplate>(`/settings/email-layout-templates/${layoutType}/`)
  },
  update(layoutType: string, data: EmailLayoutTemplateUpdate) {
    return apiClient.put<EmailLayoutTemplate>(`/settings/email-layout-templates/${layoutType}/`, data)
  },
  reset(layoutType: string) {
    return apiClient.post<EmailLayoutTemplate>(`/settings/email-layout-templates/${layoutType}/reset/`)
  },
}
