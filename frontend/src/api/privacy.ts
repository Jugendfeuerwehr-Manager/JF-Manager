/** Privacy API: legal texts and consent records – HTTP only. */

import apiClient from './index'
import type {
  ConsentCreate,
  ConsentKind,
  ConsentKindInput,
  ConsentRecord,
  ConsentSubject,
  LegalPage,
  LegalPageDraft,
  LegalPageKind,
  LegalPageVersion,
  PublicLegalPage,
} from '@/types/privacy'

export const privacyApi = {
  legalPages: () => apiClient.get<LegalPage[]>('/privacy/legal-pages/'),
  saveDraft: (kind: LegalPageKind, data: LegalPageDraft) =>
    apiClient.patch<LegalPage>(`/privacy/legal-pages/${kind}/`, data),
  publish: (kind: LegalPageKind, changeNote: string) =>
    apiClient.post<LegalPage>(`/privacy/legal-pages/${kind}/publish/`, { change_note: changeNote }),
  versions: (kind: LegalPageKind) => apiClient.get<LegalPageVersion[]>(`/privacy/legal-pages/${kind}/versions/`),
  publicPage: (kind: LegalPageKind) => apiClient.get<PublicLegalPage>(`/legal/${kind}/`),
  consents: (subject: ConsentSubject) =>
    apiClient.get<ConsentRecord[]>('/privacy/consents/', { params: { [subject.field]: subject.id } }),
  subjectAccess: (subject: ConsentSubject) =>
    apiClient.get<Blob>('/privacy/subject-access/', { params: { [subject.field]: subject.id }, responseType: 'blob' }),
  recordConsent: (subject: ConsentSubject, data: ConsentCreate) =>
    apiClient.post<ConsentRecord>('/privacy/consents/', { ...data, [subject.field]: subject.id }),
  consentKinds: () => apiClient.get<ConsentKind[]>('/privacy/consent-kinds/'),
  createConsentKind: (data: ConsentKindInput) => apiClient.post<ConsentKind>('/privacy/consent-kinds/', data),
  updateConsentKind: (id: number, data: Partial<ConsentKindInput>) =>
    apiClient.patch<ConsentKind>(`/privacy/consent-kinds/${id}/`, data),
  deleteConsentKind: (id: number) => apiClient.delete(`/privacy/consent-kinds/${id}/`),
}
