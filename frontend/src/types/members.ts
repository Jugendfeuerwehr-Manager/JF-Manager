/**
 * TypeScript types for the Members domain.
 * Canonical source — import from here, not from @/types/api.
 */

export interface Status {
  id: number
  name: string
  color: string
}

export interface Group {
  id: number
  name: string
  department?: number | null
}

export interface Member {
  id: number
  name: string
  lastname: string
  full_name: string
  birthday: string | null
  age: number
  email: string
  street: string
  zip_code: string
  city: string
  phone: string
  mobile: string
  notes: string
  joined: string | null
  identityCardNumber: string
  canSwimm: boolean
  gender: 'male' | 'female' | 'diverse' | ''
  status: Status | null
  group: Group | null
  storage_location: number | null
  avatar: string | null
  avatar_url: string | null
  parents?: import('@/types/parents').Parent[]
  has_alert: boolean
  department_ids: number[]
}

export interface MemberCreate {
  name: string
  lastname: string
  birthday?: string | null
  email?: string
  street?: string
  zip_code?: string
  city?: string
  phone?: string
  mobile?: string
  notes?: string
  joined?: string | null
  identityCardNumber?: string
  canSwimm?: boolean
  gender?: 'male' | 'female' | 'diverse' | ''
  status?: number | null
  group?: number | null
  storage_location?: number | null
  avatar?: File | null
}

// ─── Members list view contracts ────────────────────────────────────────────

export interface MemberFilters {
  search: string
  status: number | null
  group: number | null
  gender: string
}

export interface MemberLazyParams {
  first: number
  rows: number
  sortField: string
  sortOrder: 1 | -1
}

export interface MemberStatsBucket {
  label: string
  color?: string
  count?: number
}

export interface MemberStats {
  total: number
  gender: {
    male?: number
    female?: number
    diverse?: number
    unknown?: number
  }
  age?: {
    avg?: number | null
    min?: number
    max?: number
    buckets?: MemberStatsBucket[]
  } | null
  by_status: { name: string; count: number; color: string }[]
  can_swim: number
  by_group: { name: string; count: number }[]
}
