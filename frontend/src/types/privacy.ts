/** Legal texts (imprint, privacy notice) and consent records (DSGVO). */

export type LegalPageKind = 'imprint' | 'privacy' | 'portal_terms'

/** Public route of each legal text. */
export const LEGAL_PAGE_PATHS: Record<LegalPageKind, string> = {
  imprint: '/impressum',
  privacy: '/datenschutz',
  portal_terms: '/nutzungsregeln',
}

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

/** A kind of consent; admins add their own in the privacy settings. */
export interface ConsentKind {
  id: number
  slug: string
  label: string
  /** Wording people agree to; a change raises ``version``. */
  description: string
  version: number
  /** Parents grant and withdraw it in the portal for each child. */
  in_portal: boolean
  active: boolean
  built_in: boolean
  position: number
}

export type ConsentKindInput = Pick<ConsentKind, 'slug' | 'label' | 'description' | 'in_portal' | 'active' | 'position'>

/** Portal: consents per child. */
export interface PortalConsentEntry {
  status: ConsentStatus
  recorded_at: string
  recorded_by_name: string
  source: string
  text_version: string
}

export interface PortalConsentOverview {
  kinds: Array<Pick<ConsentKind, 'slug' | 'label' | 'description' | 'version'>>
  people: Array<{ member_id: number, name: string, consents: Record<string, PortalConsentEntry | null> }>
}
