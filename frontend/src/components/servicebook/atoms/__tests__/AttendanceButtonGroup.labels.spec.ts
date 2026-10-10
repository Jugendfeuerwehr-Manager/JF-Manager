import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AttendanceButtonGroup from '../AttendanceButtonGroup.vue'
import { AttendanceState, AttendanceStateLabels } from '@/types/servicebook'

describe('attendance labels (UX-04.1)', () => {
  it('uses one wording for every attendance view', () => {
    expect(Object.values(AttendanceStateLabels)).toEqual(['Anwesend', 'Entschuldigt', 'Fehlt'])
    const wrapper = mount(AttendanceButtonGroup, { props: { currentState: AttendanceState.ABSENT } })
    const text = wrapper.html()
    for (const label of Object.values(AttendanceStateLabels)) expect(text).toContain(label)
    expect(text).not.toContain('Fehlend')
  })
})
