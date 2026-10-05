/**
 * Public Branding API Client
 * Fetches public branding information — no authentication required.
 */

import axios from 'axios'
import type { PublicBranding } from '@/types/settings'

// Same origin as the app (see docs/operations/session-auth.md).
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const brandingApi = {
  /**
   * Get public branding info (title, slug, logo_url, brand_color)
   * GET /api/v1/app/branding/
   */
  getPublicBranding() {
    return axios.get<PublicBranding>(`${baseURL}/app/branding/`)
  },
}
