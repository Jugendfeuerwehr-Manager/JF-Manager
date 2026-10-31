/**
 * TypeScript types for the Parents domain.
 * Canonical source — import from here, not from @/types/api.
 */

export interface Parent {
  id: number
  name: string
  lastname: string
  full_name: string
  email: string
  email2: string
  phone: string
  mobile: string
  street: string
  zip_code: string
  city: string
  notes: string
  /** Portal: the other parent may see this contact (opt-in, DSGVO). */
  share_contact_with_coparent?: boolean
  children: number[]
}

export interface ParentCreate {
  name: string
  lastname: string
  email: string
  email2?: string
  phone?: string
  mobile?: string
  street?: string
  zip_code?: string
  city?: string
  notes?: string
  share_contact_with_coparent?: boolean
  children?: number[]
}
