/** Staff inbox "Eingang" (NOTIF-01.2): tasks with a team status and notices with a personal read state. */
import apiClient from './index'

export type InboxType = 'task' | 'notice'
export type InboxCategory = 'requests' | 'registrations' | 'staffing' | 'accounts'
export type InboxDoneVia = 'ui' | 'email_action' | 'auto'

export interface InboxEntry {
  id: number
  kind: string
  category: InboxCategory
  type: InboxType
  title: string
  count: number
  link: string
  department: string | null
  department_id: number | null
  updated_at: string
  created_at: string
  read: boolean
  task_state: 'open' | 'done' | null
  done_by: string | null
  done_at: string | null
  done_via: InboxDoneVia | null
}

export interface InboxFilters {
  type?: InboxType | ''
  category?: InboxCategory | ''
  department?: number | null
  unread?: boolean
  done?: boolean
  offset?: number
}

export interface InboxPage { count: number, results: InboxEntry[] }
export interface InboxCounts { open_tasks: number, unread_notices: number, total: number }

/** Only set filters become query parameters. */
export function inboxParams(filters: InboxFilters): Record<string, string | number> {
  const params: Record<string, string | number> = {}
  if (filters.type) params.type = filters.type
  if (filters.category) params.category = filters.category
  if (filters.department) params.department = filters.department
  if (filters.unread) params.unread = 1
  if (filters.done) params.done = 1
  if (filters.offset) params.offset = filters.offset
  return params
}

const base = '/notifications/inbox'

export const inboxApi = {
  list: (filters: InboxFilters = {}) => apiClient.get<InboxPage>(`${base}/`, { params: inboxParams(filters) }),
  counts: () => apiClient.get<InboxCounts>(`${base}/counts/`),
  markRead: (id: number) => apiClient.post<InboxEntry>(`${base}/${id}/read/`),
  markReadBulk: (ids: number[]) => apiClient.post<{ updated: number }>(`${base}/read-bulk/`, { ids }),
  markDone: (id: number) => apiClient.post<InboxEntry>(`${base}/${id}/done/`),
}
