/// <reference types="vite/client" />
import type * as ApiTypes from '../api/types'

declare module '@/types/api' {
  export type PaginatedResponse<T> = {
    count?: number
    next?: string | null
    previous?: string | null
    results: T[]
  }

  export type ID = ApiTypes.ID

  export type Member = ApiTypes.MemberDetail
  export type MemberCreate = ApiTypes.MemberCreateUpdate
  export type Parent = ApiTypes.Parent
  export type Status = ApiTypes.Status
  export type Group = ApiTypes.Group
  export type Event = ApiTypes.Event
  export type EventType = ApiTypes.EventType

  export type LoginRequest = { username: string; password: string }
  export type LoginResponse = ApiTypes.TokenObtainPair
  export type TokenRefreshRequest = { refresh: string }
  export type TokenRefreshResponse = { access: string }

  export type UserInfo = ApiTypes.UserInfo
  export type AppSettings = { [k: string]: any }

  // Re-export a few APIs for convenience
  export { default as apiTypes } from '../api/types'
}
