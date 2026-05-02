/// <reference types="vite/client" />

// Extend vue-router RouteMeta so custom meta fields are type-safe
// The import is required to make this an augmentation (not a replacement)
import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresStaff?: boolean
    requiresPerm?: string  // bare Django codename
  }
}
