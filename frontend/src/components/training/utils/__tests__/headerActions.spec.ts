import { describe, expect, it } from 'vitest'
import { headerTier, menuLabel, splitHeaderActions, type HeaderAction } from '../headerActions'

const action = (key: string, tier: HeaderAction['tier'], extra: Partial<HeaderAction> = {}): HeaderAction => ({
  key, label: key, tier, visible: true, command: () => {}, ...extra,
})

const actions = [
  action('library', 'md'),
  action('block', 'lg'),
  action('rotation', 'xl'),
  action('copy', 'menu'),
  action('hidden', 'sm', { visible: false }),
]

describe('planner header actions', () => {
  it('maps header widths to tiers', () => {
    expect(headerTier(358)).toBe('sm')
    expect(headerTier(700)).toBe('md')
    expect(headerTier(1100)).toBe('lg')
    expect(headerTier(1700)).toBe('xl')
  })

  it('moves everything into the menu on phones', () => {
    const { inline, menu } = splitHeaderActions(actions, 358)
    expect(inline).toEqual([])
    expect(menu.map((a) => a.key)).toEqual(['library', 'block', 'rotation', 'copy'])
  })

  it('shows more buttons as the header grows and never shows hidden actions', () => {
    expect(splitHeaderActions(actions, 1100).inline.map((a) => a.key)).toEqual(['library', 'block'])
    const wide = splitHeaderActions(actions, 1700)
    expect(wide.inline.map((a) => a.key)).toEqual(['library', 'block', 'rotation'])
    expect(wide.menu.map((a) => a.key)).toEqual(['copy'])
  })

  it('explains disabled menu entries', () => {
    expect(menuLabel(action('Serie', 'menu', { disabled: true, disabledReason: 'zuerst speichern' }))).toBe('Serie (zuerst speichern)')
    expect(menuLabel(action('Serie', 'menu', { disabledReason: 'zuerst speichern' }))).toBe('Serie')
  })
})
