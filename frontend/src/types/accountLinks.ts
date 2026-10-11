/** Staff account ↔ member/parent record (PORTAL-04, concept 4.10). */
export type AccountLinkStatus = 'pending' | 'confirmed' | 'rejected'
export type AccountLinkRecordKind = 'member' | 'parent'

export interface AccountLinkMember {
  id: number
  name: string
  birth_year: number | null
  departments: string[]
  group: string | null
}

export interface AccountLinkParent {
  id: number
  name: string
  children: { first_name: string, group: string | null }[]
}

export interface AccountLink {
  id: number
  status: AccountLinkStatus
  user: { id: number, username: string, name: string }
  member: AccountLinkMember | null
  parent: AccountLinkParent | null
  linked_by: string
  linked_at: string
  confirmed_at: string | null
  rejected_at: string | null
}

export interface AccountCandidate {
  id: number
  username: string
  name: string
  /** Why it is suggested: same e-mail address or same name; empty for search hits. */
  reason: 'email' | 'name' | ''
  /** Already bound to a record (a second link is refused). */
  linked: boolean
}

export interface AccountLinkPayload {
  user: number
  member?: number | null
  parent?: number | null
  transfer?: boolean
}

export interface AccountLinkResult {
  ok: boolean
  code?: string
  message?: string
}

/** Same qualification type at the linked account and at the member (PORTAL-04.4). */
export interface QualificationDuplicate {
  type: string
  account: { id: number, acquired: string | null, expires: string | null, attachments: number }
  member: { id: number, acquired: string | null, expires: string | null, attachments: number }
  same_date: boolean
}
