<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

defineProps<{ title: string, subtitle?: string, titleId: string }>()
const emit = defineEmits<{ close: [] }>()

const sheet = ref<HTMLElement | null>(null)
const heading = ref<HTMLElement | null>(null)
let opener: HTMLElement | null = null

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.stopPropagation(); emit('close'); return }
  if (event.key !== 'Tab' || !sheet.value) return
  const nodes = Array.from(sheet.value.querySelectorAll<HTMLElement>(FOCUSABLE))
  if (!nodes.length) return
  const first = nodes[0]!
  const last = nodes[nodes.length - 1]!
  const active = document.activeElement
  if (event.shiftKey && (active === first || active === heading.value)) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && active === last) { event.preventDefault(); first.focus() }
}

onMounted(async () => {
  opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  await nextTick()
  heading.value?.focus()
})
onBeforeUnmount(() => { opener?.focus?.() })
</script>

<template>
  <div class="sheet-backdrop" @click.self="emit('close')">
    <section ref="sheet" class="sheet" role="dialog" aria-modal="true" :aria-labelledby="titleId" @keydown="onKeydown">
      <div class="grip" aria-hidden="true"></div>
      <div class="head">
        <h2 :id="titleId" ref="heading" tabindex="-1">{{ title }}</h2>
        <span v-if="subtitle" class="sub">{{ subtitle }}</span>
      </div>
      <slot />
    </section>
  </div>
</template>

<style scoped>
.sheet-backdrop { position: fixed; inset: 0; z-index: 1100; display: flex; align-items: flex-end; justify-content: center; background: color-mix(in srgb, var(--p-surface-900), transparent 55%); }
.sheet { width: 100%; max-width: 40rem; max-height: 92dvh; overflow-y: auto; box-sizing: border-box; display: flex; flex-direction: column; gap: 14px; padding: 8px 16px calc(24px + env(safe-area-inset-bottom)); background: var(--p-content-background); color: var(--p-text-color); border-radius: 20px 20px 0 0; box-shadow: 0 -8px 24px color-mix(in srgb, var(--p-surface-900), transparent 82%); }
.grip { align-self: center; width: 40px; height: 4px; border-radius: 2px; background: var(--p-content-border-color); }
.head { display: flex; flex-direction: column; gap: 4px; }
h2 { margin: 0; font-size: 19px; font-weight: 700; }
h2:focus { outline: none; }
.sub { font-size: 14px; color: var(--p-text-muted-color); }
</style>
