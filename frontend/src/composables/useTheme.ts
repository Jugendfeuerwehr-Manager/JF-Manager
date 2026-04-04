import { ref, watch, onMounted, onUnmounted } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'jfm-theme-mode'
const DARK_CLASS = 'app-dark'

// Global singleton state so all components share the same mode
const themeMode = ref<ThemeMode>('system')

let systemMediaQuery: MediaQueryList | null = null
let systemListener: ((e: MediaQueryListEvent) => void) | null = null

function applyTheme(mode: ThemeMode) {
  const html = document.documentElement
  if (mode === 'dark') {
    html.classList.add(DARK_CLASS)
    removeSystemListener()
  } else if (mode === 'light') {
    html.classList.remove(DARK_CLASS)
    removeSystemListener()
  } else {
    // system — follow OS preference
    attachSystemListener()
    applySystemPreference()
  }
}

function applySystemPreference() {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  if (prefersDark) {
    document.documentElement.classList.add(DARK_CLASS)
  } else {
    document.documentElement.classList.remove(DARK_CLASS)
  }
}

function attachSystemListener() {
  if (systemMediaQuery) return
  systemMediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  systemListener = (e: MediaQueryListEvent) => {
    if (themeMode.value === 'system') {
      if (e.matches) {
        document.documentElement.classList.add(DARK_CLASS)
      } else {
        document.documentElement.classList.remove(DARK_CLASS)
      }
    }
  }
  systemMediaQuery.addEventListener('change', systemListener)
}

function removeSystemListener() {
  if (systemMediaQuery && systemListener) {
    systemMediaQuery.removeEventListener('change', systemListener)
    systemMediaQuery = null
    systemListener = null
  }
}

export function useTheme() {
  function initTheme() {
    const stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | null
    themeMode.value = stored ?? 'system'
    applyTheme(themeMode.value)
  }

  async function setMode(mode: ThemeMode) {
    themeMode.value = mode
    localStorage.setItem(STORAGE_KEY, mode)
    applyTheme(mode)

    // Persist to user profile if possible
    try {
      const { userApi } = await import('@/api/user')
      await userApi.updateProfile({ theme_mode: mode } as any)
    } catch {
      // Silently ignore — preference is still saved locally
    }
  }

  watch(themeMode, (mode) => {
    applyTheme(mode)
  })

  onUnmounted(() => {
    if (themeMode.value !== 'system') {
      removeSystemListener()
    }
  })

  return {
    themeMode,
    setMode,
    initTheme
  }
}
