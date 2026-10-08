/**
 * Dashboard summary (UX-01.1): counts only, scoped like the module lists.
 * A section is null when the user may not see that module.
 */
import apiClient from './index'

export interface DashboardSummary {
  members: { total: number } | null
  parents: { total: number } | null
  qualifications: {
    expired: number
    expiring: Record<'30' | '60' | '90', number>
    without_evidence: number
  } | null
  services: {
    upcoming_days: number
    upcoming: number
    next: { id: number; start: string; topic: string; place: string } | null
  } | null
  orders: { open: number } | null
  lists: { open: number } | null
}

export const dashboardApi = {
  summary() {
    return apiClient.get<DashboardSummary>('/dashboard/summary/')
  }
}
