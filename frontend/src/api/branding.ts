/**
 * Public Branding API Client
 * Fetches public branding information — no authentication required.
 */

import axios from 'axios'
import type { PublicBranding } from '@/types/settings'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const brandingApi = {
  /**
   * Get public branding info (title, slug, logo_url)
   * GET /api/v1/app/branding/
   */
  getPublicBranding() {
    return axios.get<PublicBranding>(`${baseURL}/app/branding/`)
  },
}
