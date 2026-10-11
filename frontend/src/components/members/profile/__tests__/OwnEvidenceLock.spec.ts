import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import QualificationsManager from '../QualificationsManager.vue'
import SpecialTasksManager from '../SpecialTasksManager.vue'

const { auth, qualifications } = vi.hoisted(() => ({
  auth: { ownMemberIds: [] as number[] },
  qualifications: {
    qualifications: [{ id: 1, type_name: 'Erste Hilfe', date_acquired: '2024-01-01', date_expires: null }],
    specialTasks: [{ id: 2, task_name: 'Kassenwart', start_date: '2024-01-01', end_date: null, is_active: true }],
    fetchQualifications: vi.fn(async () => undefined),
    fetchSpecialTasks: vi.fn(async () => undefined),
  },
}))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))
vi.mock('@/stores/qualifications', () => ({ useQualificationsStore: () => qualifications }))
vi.mock('primevue/useconfirm', () => ({ useConfirm: () => ({ require: vi.fn() }) }))
vi.mock('primevue/usetoast', () => ({ useToast: () => ({ add: vi.fn() }) }))

function render(component: typeof QualificationsManager | typeof SpecialTasksManager) {
  return mount(component, {
    props: { memberId: 5 },
    global: {
      plugins: [PrimeVue],
      directives: { tooltip: {} },
      stubs: { QualificationForm: true, SpecialTaskForm: true, AttachmentsSection: true, Dialog: true },
    },
  })
}

describe('four-eyes lock in the member profile (PORTAL-04.3)', () => {
  beforeEach(() => { auth.ownMemberIds = [] })

  for (const [name, component, label] of [
    ['qualifications', QualificationsManager, 'Qualifikation hinzufügen'],
    ['special tasks', SpecialTasksManager, 'Sonderaufgabe hinzufügen'],
  ] as const) {
    it(`hides the ${name} actions for the own record and explains why`, async () => {
      const other = render(component)
      await flushPromises()
      expect(other.text()).toContain(label)
      expect(other.find('.own-lock').exists()).toBe(false)

      auth.ownMemberIds = [5]
      const own = render(component)
      await flushPromises()
      expect(own.text()).not.toContain(label)
      expect(own.find('.action-buttons').exists()).toBe(false)
      expect(own.get('.own-lock').text()).toContain('andere Person')
    })
  }
})
