import apiClient from './index'
export type ConfigurationValue = string | number | boolean
export interface ConfigurationField {
  label: string
  type: 'boolean' | 'integer' | 'time' | 'string'
  secret: boolean
  source: 'default' | 'database' | 'environment' | 'computed'
  storage: string
  locked: boolean
  min?: number
  max?: number
  max_length?: number
  allow_blank: boolean
  /** Longer text; edited in a text area. */
  multiline?: boolean
  effective: string
  validation: string
  environment_key?: string
}
export interface ConfigurationCategory {
  label: string
  can_change: boolean
  fields: Record<string, ConfigurationField>
  view_permission: string
  change_permission: string
}
export interface ConfigurationCatalog {
  categories: Record<string, ConfigurationCategory>
  host: { label: string; storage: string; permission: string; effective: string }[]
}
export interface SetupStatus {
  organization_configured: boolean
  active_departments: number
  standard_roles: number
  expected_standard_roles: number
  administrator_assigned: boolean
  email_configured: boolean
  ldap_enabled: boolean
  oidc_enabled: boolean
  push_enabled: boolean
}
export interface OperationsWarning {
  code: string
  text: string
}
export interface OperationsStatus {
  available: boolean
  reason?: 'not_configured' | 'missing' | 'unreadable'
  instance?: string
  mode?: '' | 'compose' | 'native'
  version?: string
  workers_held?: boolean
  updated?: string
  last_backup?: {
    status: 'ok' | 'failed' | 'unknown'
    finished: string
    message: string
    last_success: string | null
  } | null
  warnings?: OperationsWarning[]
}
export const configurationApi = {
  operations: () => apiClient.get<OperationsStatus>('/settings/operations/'),
  catalog: () => apiClient.get<ConfigurationCatalog>('/settings/catalog/'),
  setup: () => apiClient.get<SetupStatus>('/settings/setup/'),
  get: (category: string) =>
    apiClient.get<Record<string, ConfigurationValue>>(`/settings/${category}/`),
  update: (category: string, values: Record<string, ConfigurationValue>) =>
    apiClient.patch<Record<string, ConfigurationValue>>(`/settings/${category}/`, values),
  generatePushKeys: (subject: string) =>
    apiClient.post<Record<string, ConfigurationValue>>('/settings/push/generate-keys/', {
      subject,
    }),
}
export function configurationError(error: unknown): string {
  const data = (error as { response?: { data?: Record<string, unknown> } })?.response?.data
  if (!data)
    return 'Die Anfrage ist fehlgeschlagen. Eingaben bleiben erhalten; bitte erneut versuchen.'
  if (typeof data.detail === 'string') return data.detail
  return (
    Object.entries(data)
      .filter(([name]) => name !== 'code')
      .map(([, value]) => value)
      .flat()
      .filter((value) => typeof value === 'string')
      .join(' ') || 'Die Einstellungen konnten nicht gespeichert werden.'
  )
}
