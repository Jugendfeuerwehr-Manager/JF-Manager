/** Quick-action links from notifications (NOTIF-01.4, E12): resolve a signed token, then execute it. */
import apiClient from './index'

export type ActionMode = 'direct' | 'confirm'
export type ActionState = 'ready' | 'done' | 'not_available'
export type ActionErrorCode = 'invalid' | 'expired' | 'wrong_account' | 'gone'

export interface ActionChoice { value: string, label: string }
export interface ActionField {
  name: string
  type: 'choice'
  label: string
  optional?: boolean
  choices: ActionChoice[]
}

export interface ActionPreview {
  action: string
  mode: ActionMode
  state: ActionState
  title: string
  lines: string[]
  target_route: string
  payload_fields?: ActionField[]
}

export interface ActionResult {
  action: string
  mode: ActionMode
  state: ActionState
  message?: string
  lines?: string[]
  target_route: string
  /** Direct actions that can be taken back carry a token for the reverse action. */
  undo?: { label: string, token: string }
}

export interface ActionErrorBody { code: ActionErrorCode, detail: string, target_route: string }

export const actionsApi = {
  resolve: (token: string) => apiClient.post<ActionPreview>('/actions/resolve/', { token }),
  execute: (token: string, payload: Record<string, string> = {}) =>
    apiClient.post<ActionResult>('/actions/execute/', { token, payload }),
}
