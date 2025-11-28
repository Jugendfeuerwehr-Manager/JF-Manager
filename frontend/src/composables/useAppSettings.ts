/**
 * Composable for accessing application settings
 * Provides reactive access to settings like website title
 */

import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settings'

export function useAppSettings() {
  const settingsStore = useSettingsStore()

  /**
   * Get the website title from settings
   * Falls back to 'JF-Manager' if not set
   */
  const websiteTitle = computed(() => {
    return settingsStore.general?.title || 'JF-Manager'
  })

  /**
   * Set the document title
   * Useful for page-specific titles
   */
  function setDocumentTitle(pageTitle?: string) {
    if (pageTitle) {
      document.title = `${pageTitle} - ${websiteTitle.value}`
    } else {
      document.title = websiteTitle.value
    }
  }

  return {
    websiteTitle,
    setDocumentTitle
  }
}
