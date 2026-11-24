<template>
  <div class="signature">
    <!-- Read-only (review, sealed application): the stored image, nothing to draw on. -->
    <template v-if="disabled">
      <img v-if="modelValue" :src="modelValue" :alt="label" class="signature__image" />
      <p v-else class="signature__empty">Nicht unterschrieben</p>
    </template>
    <canvas
      v-else
      ref="canvas"
      class="signature__canvas"
      :aria-label="label"
      role="img"
      @pointerdown="start"
      @pointermove="draw"
      @pointerup="stop"
      @pointerleave="stop"
      @pointercancel="stop"
    ></canvas>
    <div v-if="!disabled" class="signature__bar">
      <span class="signature__hint">{{ modelValue ? 'Unterschrieben' : 'Mit Finger, Stift oder Maus unterschreiben' }}</span>
      <AdmButton variant="ghost" icon="pi pi-eraser" :disabled="disabled || !modelValue" @click="clear">Löschen</AdmButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AdmButton from './AdmButton.vue'

interface Props {
  label: string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), { disabled: false })
const modelValue = defineModel<string>({ default: '' })
const canvas = ref<HTMLCanvasElement | null>(null)
let drawing = false
// What the pad itself emitted last; anything else came from outside and is redrawn.
let emitted = ''
let resizeObserver: ResizeObserver | null = null

function context() {
  return canvas.value?.getContext('2d') ?? null
}

function fit() {
  const element = canvas.value
  if (!element) return
  const ratio = window.devicePixelRatio || 1
  const { width, height } = element.getBoundingClientRect()
  element.width = Math.round(width * ratio)
  element.height = Math.round(height * ratio)
  const ctx = context()
  if (!ctx) return
  ctx.scale(ratio, ratio)
  ctx.lineWidth = 2.2
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  // Ink and paper stay black on white in every theme: the signature is printed.
  ctx.strokeStyle = 'black'
  // Resizing wipes the canvas; a stored signature is redrawn so it stays visible.
  if (modelValue.value) restore(modelValue.value)
}

function restore(dataUrl: string) {
  const image = new Image()
  image.onload = () => {
    const element = canvas.value
    const ctx = context()
    if (!element || !ctx) return
    const { width, height } = element.getBoundingClientRect()
    ctx.drawImage(image, 0, 0, width, height)
  }
  image.src = dataUrl
}

function point(event: PointerEvent) {
  const rect = canvas.value!.getBoundingClientRect()
  return { x: event.clientX - rect.left, y: event.clientY - rect.top }
}

function start(event: PointerEvent) {
  if (props.disabled) return
  const ctx = context()
  if (!ctx) return
  drawing = true
  canvas.value!.setPointerCapture(event.pointerId)
  const { x, y } = point(event)
  ctx.beginPath()
  ctx.moveTo(x, y)
}

function draw(event: PointerEvent) {
  if (!drawing) return
  const ctx = context()
  if (!ctx) return
  const { x, y } = point(event)
  ctx.lineTo(x, y)
  ctx.stroke()
}

function stop() {
  if (!drawing) return
  drawing = false
  emitted = canvas.value!.toDataURL('image/png')
  modelValue.value = emitted
}

function clear() {
  const element = canvas.value
  const ctx = context()
  if (!element || !ctx) return
  ctx.clearRect(0, 0, element.width, element.height)
  emitted = ''
  modelValue.value = ''
}

watch(modelValue, (value) => {
  if (value === emitted) return
  const element = canvas.value
  const ctx = context()
  if (!element || !ctx) return
  ctx.clearRect(0, 0, element.width, element.height)
  emitted = value
  if (value) restore(value)
})

onMounted(() => {
  fit()
  if (typeof ResizeObserver === 'undefined' || !canvas.value) return
  resizeObserver = new ResizeObserver(fit)
  resizeObserver.observe(canvas.value)
})
onBeforeUnmount(() => resizeObserver?.disconnect())
</script>

<style scoped>
.signature {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
}

.signature__canvas {
  width: 100%;
  height: 160px;
  border: 1px dashed var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: white;
  touch-action: none;
  cursor: crosshair;
}

.signature__image {
  width: 100%;
  height: 160px;
  object-fit: contain;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: white;
}

.signature__empty {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.signature__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--jf-space-1);
}

.signature__hint {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}
</style>
