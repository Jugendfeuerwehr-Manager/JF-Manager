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
