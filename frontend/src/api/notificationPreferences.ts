import apiClient from './index'

export interface NotificationPreference { kind: string, label: string, email: boolean, push: boolean }

export const notificationPreferencesApi = {
  list() {
    return apiClient.get<NotificationPreference[]>('/notifications/preferences/')
  },
  save(rows: Pick<NotificationPreference, 'kind' | 'email' | 'push'>[]) {
    return apiClient.put<NotificationPreference[]>('/notifications/preferences/', rows)
  },
}
