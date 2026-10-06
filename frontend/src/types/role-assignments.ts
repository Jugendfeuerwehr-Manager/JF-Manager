export interface RoleAssignmentChoice {
  id: number
  name: string
  description: string
  scope: 'organization' | 'department'
  department_ids: (number | null)[]
}
export interface RoleAssignmentOptions {
  people: { id: number; name: string }[]
  departments: { id: number; name: string }[]
  organization_allowed: boolean
  roles: RoleAssignmentChoice[]
}
export interface RoleExplanation {
  role: string
  template_id: number | null
  department_id: number | null
  department: string
  sources: { source: 'local' | 'ldap' | 'oidc'; source_key: string }[]
  permissions: string[]
}
export interface RoleAssignmentInput {
  user_id: number
  department_id: number | null
  template_id: number
  operation: 'add' | 'remove'
}
export interface RoleAssignmentPreview {
  fingerprint: string
  person: { id: number; name: string }
  role: { id: number; name: string; description: string }
  department: { id: number; name: string } | null
  operation: 'add' | 'remove'
  changed: boolean
  retained_external: boolean
  permissions: string[]
  added_permissions: string[]
  removed_permissions: string[]
  effect: string
}
