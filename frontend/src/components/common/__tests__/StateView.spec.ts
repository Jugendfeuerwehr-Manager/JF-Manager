import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import StateView, { stateForError } from '../StateView.vue'
import StatusBadge from '../StatusBadge.vue'
import { classifyApiError } from '@/utils/apiError'

describe('StateView', () => {
  it('distinguishes missing permission from an empty result', () => {
    const empty = mount(StateView, { props: { kind: 'empty' } })
    const forbidden = mount(StateView, { props: { kind: 'forbidden' } })
    expect(empty.text()).toContain('Noch keine Einträge')
    expect(forbidden.text()).toContain('Keine Berechtigung')
    expect(empty.attributes('role')).toBe('status')
    expect(forbidden.find('button').exists()).toBe(false)
  })

  it('announces failures and offers a retry', async () => {
    const wrapper = mount(StateView, { props: { kind: 'offline' } })
    expect(wrapper.attributes('role')).toBe('alert')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('marks loading as busy and accepts custom text and actions', () => {
    const loading = mount(StateView, { props: { kind: 'loading' } })
    expect(loading.attributes('aria-busy')).toBe('true')
    const custom = mount(StateView, {
      props: { kind: 'empty', title: 'Keine Mitglieder', message: 'Lege das erste Mitglied an.' },
      slots: { default: '<a href="/members/new">Mitglied anlegen</a>' },
    })
    expect(custom.text()).toContain('Keine Mitglieder')
    expect(custom.find('a[href="/members/new"]').exists()).toBe(true)
  })
})

describe('classifyApiError', () => {
  it.each([
    [{ message: 'Network Error' }, 'network', 'offline'],
    [{ response: { status: 401 } }, 'unauthorized', 'error'],
    [{ response: { status: 403 } }, 'forbidden', 'forbidden'],
    [{ response: { status: 404 } }, 'not_found', 'error'],
    [{ response: { status: 409 } }, 'conflict', 'error'],
    [{ response: { status: 400 } }, 'validation', 'error'],
    [{ response: { status: 503 } }, 'server', 'error'],
  ])('classifies %o as %s', (error, kind, state) => {
    expect(classifyApiError(error)).toBe(kind)
    expect(stateForError(classifyApiError(error))).toBe(state)
  })
})

describe('StatusBadge', () => {
  it('always shows a symbol next to the text', () => {
    const wrapper = mount(StatusBadge, { props: { label: 'Abgelaufen', severity: 'danger' } })
    expect(wrapper.text()).toBe('Abgelaufen')
    expect(wrapper.find('i.pi-times-circle').attributes('aria-hidden')).toBe('true')
    expect(wrapper.classes()).toContain('status-badge--danger')
  })

  it('accepts a specific symbol', () => {
    const wrapper = mount(StatusBadge, { props: { label: 'Entwurf', icon: 'pi pi-pencil' } })
    expect(wrapper.find('i.pi-pencil').exists()).toBe(true)
  })
})
