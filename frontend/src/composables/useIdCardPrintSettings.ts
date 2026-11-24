/**
 * Printer calibration for DJF cards: offset, paper tone and colour correction. It belongs to
 * the printer at hand, so it is kept per browser; without storage the defaults apply.
 */
import { reactive, watch } from 'vue'
import { DEFAULT_PAPER } from '@/utils/idCardPhoto'

const KEY = 'jf.idCardPrint'

export interface IdCardPrintSettings {
  offsetX: number
  offsetY: number
  paper: string
  strength: number
}

const DEFAULTS: IdCardPrintSettings = { offsetX: 0, offsetY: 0, paper: DEFAULT_PAPER, strength: 0.6 }

function load(): IdCardPrintSettings {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) ?? '{}') as Partial<IdCardPrintSettings>
    return { ...DEFAULTS, ...stored }
  } catch {
    return { ...DEFAULTS }
  }
}

export function useIdCardPrintSettings() {
  const settings = reactive(load())
  watch(settings, (value) => {
    try {
      localStorage.setItem(KEY, JSON.stringify(value))
    } catch {
      // private window or blocked storage: the settings just do not stick
    }
  })
  function reset() {
    Object.assign(settings, DEFAULTS)
  }
  return { settings, reset }
}
