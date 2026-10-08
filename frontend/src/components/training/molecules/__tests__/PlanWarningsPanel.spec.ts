import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PlanWarningsPanel from '../PlanWarningsPanel.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'

describe('PlanWarningsPanel', () => {
  it('starts collapsed, expands on demand and focuses the affected block', async () => {
    setActivePinia(createPinia())
    const store = useTrainingPlannerStore()
    store.warnings = [{ code: 'material', message: 'Material „C-Schlauch“: gleichzeitig 4 benötigt, rechnerisch 3 verfügbar', blocks: ['7'], other_session: null, blockIds: [7] }]
    const wrapper = mount(PlanWarningsPanel, { global: { stubs: {
      Button: { props: ['label'], emits: ['click'], template: '<button v-bind="$attrs" @click="$emit(\'click\')">{{ label }}</button>' },
    } } })
    expect(wrapper.text()).toContain('1 Planungswarnung')
    expect(wrapper.text()).not.toContain('C-Schlauch')
    const toggle = wrapper.findAll('button').find((b) => b.text() === 'Anzeigen')!
    expect(toggle.attributes('aria-expanded')).toBe('false')
    await toggle.trigger('click')
    expect(wrapper.text()).toContain('C-Schlauch')
    // A re-check with new warnings keeps the panel as the user left it.
    store.warnings = [...store.warnings]
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('button').find((b) => b.text() === 'Ausblenden')!.attributes('aria-expanded')).toBe('true')
    await wrapper.findAll('button').find((b) => b.text() === 'Baustein zeigen')!.trigger('click')
    expect(wrapper.emitted('focus-block')).toEqual([[7]])
    store.warnings = []
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Keine Planungswarnungen')
  })
})
