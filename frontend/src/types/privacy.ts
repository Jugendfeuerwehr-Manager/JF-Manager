/** Legal texts (imprint, privacy notice) and consent records (DSGVO). */

export type LegalPageKind = 'imprint' | 'privacy'

export interface LegalPageVersion {
  version: number
  title: string
  body: string
  change_note: string
  published_at: string
  published_by_name: string
}

export interface LegalPage {
  kind: LegalPageKind
  label: string
  draft_title: string
  draft_body: string
  updated_at: string
  updated_by_name: string
  current_version: LegalPageVersion | null
  has_unpublished_changes: boolean
}

export interface LegalPageDraft {
  draft_title?: string
  draft_body?: string
}

export interface PublicLegalPage {
  kind: LegalPageKind
  version: number
  title: string
  body: string
  published_at: string
}

export type ConsentSubjectField = 'member' | 'parent' | 'user'

export interface ConsentSubject {
  field: ConsentSubjectField
  id: number
}

export type ConsentStatus = 'granted' | 'withdrawn'

export interface ConsentRecord {
  id: number
  kind: string
  kind_label: string
  status: ConsentStatus
  status_label: string
  source: string
  source_label: string
  text_version: string
  recorded_at: string
  recorded_by_name: string
  note: string
}

export interface ConsentCreate {
  kind: string
  status: ConsentStatus
  note?: string
  text_version?: string
}

/** Kinds offered when recording a consent by hand. */
export const CONSENT_KIND_OPTIONS: Record<ConsentSubjectField, Array<{ value: string, label: string }>> = {
  member: [
    { value: 'photo_internal', label: 'Fotos intern (App, Aushang, Gruppen)' },
    { value: 'photo_public', label: 'Fotos öffentlich (Website, Presse, soziale Medien)' },
    { value: 'data_processing_guardian', label: 'Einwilligung der Sorgeberechtigten in die Datenverarbeitung' },
    { value: 'privacy_notice_ack', label: 'Datenschutzhinweise zur Kenntnis genommen' },
  ],
  parent: [
    { value: 'privacy_notice_ack', label: 'Datenschutzhinweise zur Kenntnis genommen' },
    { value: 'data_processing_guardian', label: 'Einwilligung der Sorgeberechtigten in die Datenverarbeitung' },
  ],
  user: [
    { value: 'confidentiality', label: 'Verpflichtung auf Vertraulichkeit' },
    { value: 'privacy_notice_ack', label: 'Datenschutzhinweise zur Kenntnis genommen' },
  ],
}
