/*
  Use the generated OpenAPI types as the canonical source of truth and
  provide a small set of convenience aliases used across the app. This file
  re-exports the generated `openapi-types.ts` content and maps frequently used
  shapes to easier names.
*/

import * as OpenAPI from './openapi-types'

// Re-export the generated OpenAPI namespace for ad-hoc imports
export { OpenAPI }

// Convenience aliases for models used in the frontend
export type ID = number | string

// Extract common models from components.schemas where possible
// Use optional chaining in types: fall back to a permissive `any` if the
// component doesn't exist in the generated file.
export type User = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['User'] extends infer U
      ? U
      : any
    : any
  : any

export type UserInfo = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['UserInfo'] extends infer U
      ? U
      : any
    : any
  : any

export type Member = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['MemberDetail'] extends infer M
      ? M
      : any
    : any
  : any

export type MemberCreate = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['MemberCreateUpdate'] extends infer MC
      ? MC
      : any
    : any
  : any

export type Parent = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['Parent'] extends infer P
      ? P
      : any
    : any
  : any

export type Status = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['Status'] extends infer St
      ? St
      : any
    : any
  : any

export type Group = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['Group'] extends infer G
      ? G
      : any
    : any
  : any

export type Event = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['Event'] extends infer E
      ? E
      : any
    : any
  : any

export type EventType = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['EventType'] extends infer Et
      ? Et
      : any
    : any
  : any

export type PaginatedResponse<T> = {
  count?: number
  next?: string | null
  previous?: string | null
  results: T[]
}

export type TokenObtainPair = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['TokenObtainPair'] extends infer T
      ? T
      : any
    : any
  : any

export type TokenRefresh = OpenAPI.components extends { schemas: infer S }
  ? S extends Record<string, any>
    ? S['TokenRefresh'] extends infer T
      ? T
      : any
    : any
  : any

export type LoginRequest = { username: string; password: string }
export type LoginResponse = TokenObtainPair

export default {} as const
