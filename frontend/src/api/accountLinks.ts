import apiClient from './index'
import type { AccountCandidate, AccountLink, AccountLinkPayload, AccountLinkRecordKind } from '@/types/accountLinks'

const BASE = '/portal/account-links/'

export const accountLinksApi = {
  forRecord(kind: AccountLinkRecordKind, id: number) {
    return apiClient.get<{ results: AccountLink[] }>(BASE, { params: { [kind]: id } })
  },
  suggestions(kind: AccountLinkRecordKind, id: number) {
    return apiClient.get<{ results: AccountCandidate[] }>(`${BASE}suggestions/`, { params: { [kind]: id } })
  },
  searchAccounts(search: string) {
    return apiClient.get<{ results: AccountCandidate[] }>(`${BASE}accounts/`, { params: { search } })
  },
  link(payload: AccountLinkPayload) {
    return apiClient.post<AccountLink>(BASE, payload)
  },
  unlink(id: number, target?: AccountLinkRecordKind) {
    return apiClient.delete<AccountLink | ''>(`${BASE}${id}/`, { params: target ? { target } : {} })
  },
  pendingForMe() {
    return apiClient.get<{ link: AccountLink | null }>(`${BASE}pending-for-me/`)
  },
  confirm(id: number) {
    return apiClient.post<AccountLink>(`${BASE}${id}/confirm/`)
  },
  reject(id: number) {
    return apiClient.post<AccountLink>(`${BASE}${id}/reject/`)
  },
  requestRelease() {
    return apiClient.post<{ requested: boolean, new: boolean }>(`${BASE}release-request/`)
  },
}
