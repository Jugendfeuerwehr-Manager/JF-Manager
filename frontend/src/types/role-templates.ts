export interface RoleTemplate {
  id: number
  key: string
  name: string
  description: string
  template_version: number
  scope: 'organization' | 'department' | 'both'
  delegation_approved?: boolean
  is_delegable: boolean
  is_archived: boolean
  group: { id: number; name: string } | null
}

export interface RoleTemplateComparison extends RoleTemplate {
  actual_permissions: string[]
  expected_permissions: string[] | null
  expected_metadata: Record<string, string | boolean | number> | null
  metadata_differences: Record<string, { actual: unknown; expected: unknown }> | null
  missing_permissions: string[] | null
  extra_permissions: string[] | null
  assignment_counts: {
    global_users: number
    staff_users: number
    department_roles: number
    ldap_mappings: number
    oidc_mappings: number
  }
  fingerprint: string
}

export interface RoleTemplateList {
  count: number
  next: string | null
  results: RoleTemplate[]
}
