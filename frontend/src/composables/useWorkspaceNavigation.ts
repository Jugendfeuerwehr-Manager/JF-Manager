import { ref } from 'vue'

const STORAGE_KEY = 'jf-workspace-nav-hidden'

function readStored(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

/** Shared across the app: workspace views (e.g. the training planner) may hide the desktop navigation. */
const navHidden = ref(readStored())

export function useWorkspaceNavigation() {
  function setNavHidden(hidden: boolean) {
    navHidden.value = hidden
    try {
      localStorage.setItem(STORAGE_KEY, hidden ? '1' : '0')
    } catch {
      // Storage may be unavailable (private mode); the choice then lasts for this visit only.
    }
  }

  return { navHidden, setNavHidden, toggleNav: () => setNavHidden(!navHidden.value) }
}
