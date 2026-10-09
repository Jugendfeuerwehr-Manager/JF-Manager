import { describe, expect, it } from 'vitest'
import { TRAINING_STATUS, trainingStatusMeta } from '../trainingStatus'

describe('trainingStatusMeta', () => {
  it('gives every status its own label and symbol', () => {
    const entries = Object.values(TRAINING_STATUS)
    expect(new Set(entries.map((e) => e.icon)).size).toBe(entries.length)
    expect(new Set(entries.map((e) => e.label)).size).toBe(entries.length)
  })

  it('falls back to draft when the status is missing', () => {
    expect(trainingStatusMeta(undefined).label).toBe('Entwurf')
    expect(trainingStatusMeta('cancelled').label).toBe('Abgesagt')
  })
})
