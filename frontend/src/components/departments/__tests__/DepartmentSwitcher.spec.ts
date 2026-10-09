import { beforeEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import DepartmentSwitcher from '../atoms/DepartmentSwitcher.vue'
import { useDepartmentsStore } from '@/stores/departments'
import { useAuthStore } from '@/stores/auth'

function setup(orgWide: boolean, active: number | null, compact = false) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  ;(auth as unknown as { user: unknown }).user = { has_org_wide_access: orgWide }
  const store = useDepartmentsStore()
  store.departments = [{ id: 1, name: 'Nord', code: 'N', color: '#123456' }] as never
  store.activeDepartmentId = active
  return { store, wrapper: mount(DepartmentSwitcher, { props: { compact }, global: { plugins: [pinia, PrimeVue] } }) }
}

describe('DepartmentSwitcher', () => {
  beforeEach(() => {
    localStorage.clear()
    window.matchMedia = ((query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => {},
      removeEventListener: () => {},
      addListener: () => {},
      removeListener: () => {},
    })) as unknown as typeof window.matchMedia
  })

  it('shows "Alle Abteilungen" for org-wide users without selection', () => {
    const { wrapper } = setup(true, null)
    expect(wrapper.text()).toContain('Alle Abteilungen')
    expect(wrapper.text()).not.toContain('Abteilung wählen')
    expect(wrapper.find('.pi-globe').exists()).toBe(true)
  })

  it('shows the concrete department when one is active', () => {
    const { wrapper } = setup(true, 1)
    expect(wrapper.text()).toContain('Nord (N)')
  })

  it('shows "Alle Abteilungen" in the compact variant', () => {
    const { wrapper } = setup(true, null, true)
    expect(wrapper.text()).toContain('Alle Abteilungen')
  })

  it('keeps null in the store for the all option', () => {
    const { store } = setup(true, 1)
    store.setActiveDepartment(null)
    expect(store.activeDepartmentId).toBeNull()
  })
})
