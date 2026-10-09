import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import {
  LIBRARY_MAX_WIDTH,
  LIBRARY_MIN_WIDTH,
  clampLibraryWidth,
  defaultLibraryWidth,
  usePlannerLibraryPanel,
} from '../usePlannerLibraryPanel'

function setViewport(width: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
}

function key(name: string, shiftKey = false) {
  return new KeyboardEvent('keydown', { key: name, shiftKey, cancelable: true })
}

describe('planner library panel size', () => {
  beforeEach(() => {
    localStorage.clear()
    setViewport(1440)
  })
  afterEach(() => vi.restoreAllMocks())

  it('scales the default width with the screen and keeps limits', () => {
    expect(defaultLibraryWidth(1280)).toBe(320)
    expect(defaultLibraryWidth(1920)).toBe(422)
    expect(defaultLibraryWidth(2560)).toBe(480)
    expect(clampLibraryWidth(100)).toBe(LIBRARY_MIN_WIDTH)
    expect(clampLibraryWidth(5000)).toBe(LIBRARY_MAX_WIDTH)
  })

  it('opens by default only on large screens', () => {
    expect(usePlannerLibraryPanel(ref(1)).open.value).toBe(false)
    setViewport(1920)
    expect(usePlannerLibraryPanel(ref(1)).open.value).toBe(true)
  })

  it('remembers width and visibility per user', async () => {
    const user = ref<number | null>(1)
    const panel = usePlannerLibraryPanel(user)
    panel.setWidth(500)
    panel.setOpen(true)
    expect(JSON.parse(localStorage.getItem('jf-planner-library:1')!)).toEqual({ width: 500, open: true })

    user.value = 2
    await nextTick()
    expect(panel.width.value).toBe(defaultLibraryWidth(1440))
    expect(panel.open.value).toBe(false)

    const again = usePlannerLibraryPanel(ref(1))
    expect(again.width.value).toBe(500)
    expect(again.open.value).toBe(true)
  })

  it('resizes with the keyboard like a separator', () => {
    const panel = usePlannerLibraryPanel(ref(1))
    panel.setWidth(400)
    const widen = key('ArrowLeft')
    expect(panel.onSeparatorKey(widen)).toBe(true)
    expect(widen.defaultPrevented).toBe(true)
    expect(panel.width.value).toBe(416)
    panel.onSeparatorKey(key('ArrowRight', true))
    expect(panel.width.value).toBe(352)
    panel.onSeparatorKey(key('End'))
    expect(panel.width.value).toBe(LIBRARY_MAX_WIDTH)
    panel.onSeparatorKey(key('Home'))
    expect(panel.width.value).toBe(LIBRARY_MIN_WIDTH)
    panel.onSeparatorKey(key('Enter'))
    expect(panel.width.value).toBe(defaultLibraryWidth(1440))
    expect(panel.onSeparatorKey(key('a'))).toBe(false)
  })

  it('keeps working when storage is unavailable or holds invalid data', () => {
    localStorage.setItem('jf-planner-library:1', '{broken')
    expect(usePlannerLibraryPanel(ref(1)).width.value).toBe(defaultLibraryWidth(1440))
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked') })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked') })
    const panel = usePlannerLibraryPanel(ref(1))
    expect(() => panel.setWidth(600)).not.toThrow()
    expect(panel.width.value).toBe(600)
  })
})
