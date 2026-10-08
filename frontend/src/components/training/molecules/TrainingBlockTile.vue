<template>
  <div class="block-tile"
    :data-block-id="block.id"
    tabindex="0"
    role="group"
    :aria-label="`${kindLabel ? kindLabel + ': ' : ''}${block.title}${block.location ? ', ' + block.location : ''}${block.station_key ? ', verknüpfte Station' : ''}, ab Minute ${block.start_offset_minutes}, ${block.duration_minutes} Minuten. ${readOnly ? 'Enter: Details ansehen.' : 'Enter: bearbeiten. Pfeiltasten auf/ab: verschieben, mit Alt: Dauer ändern.'}`"
    @keydown="onKeydown"
    :style="tileStyle"
    :class="{ selected: selected, dragging: isDragging, 'read-only': readOnly }"
    @click.stop="emit('click', block)"
  >
    <span class="tile-title">{{ block.title }}</span>
    <span class="tile-meta"><i v-if="block.station_key" class="pi pi-link tile-link" aria-hidden="true" title="Verknüpfte Station"></i>{{ [kindLabel, durationLabel, block.location].filter(Boolean).join(' · ') }}</span>
    <div v-if="!readOnly" class="tile-actions">
      <Button icon="pi pi-pencil" text size="small" severity="secondary" :aria-label="`${block.title} bearbeiten`" @click.stop="emit('edit', block)" />
      <Button icon="pi pi-trash" text size="small" severity="danger" :aria-label="`${block.title} entfernen`" @click.stop="emit('remove', block.id)" />
    </div>
    <div v-if="!readOnly" class="resize-handle" title="Dauer ändern" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import { formatDuration } from '../utils/duration'
import { safeBlockColor } from '../utils/blockColor'
import { BLOCK_KIND_LABELS, type PlannerBlock, type TrainingBlockMove } from '@/types/training'

interface Props {
  block: PlannerBlock
  readOnly?: boolean
  selected?: boolean
  minuteHeight?: number // px per minute
}

const props = withDefaults(defineProps<Props>(), { selected: false, minuteHeight: 2, readOnly: false })

const emit = defineEmits<{
  click: [block: PlannerBlock]
  edit: [block: PlannerBlock]
  remove: [id: number]
  move: [id: number, values: TrainingBlockMove]
}>()

function onKeydown(event: KeyboardEvent) {
  if (event.target !== event.currentTarget) return
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    emit('edit', props.block)
  } else if (!props.readOnly && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
    event.preventDefault()
    const delta = (event.key === 'ArrowDown' ? 1 : -1) * (event.shiftKey ? 1 : 5)
    emit('move', props.block.id, event.altKey
      ? { duration_minutes: props.block.duration_minutes + delta }
      : { start_offset_minutes: props.block.start_offset_minutes + delta })
  }
}

const isDragging = ref(false)
const durationLabel = computed(() => formatDuration(props.block.duration_minutes))
// Plain blocks stay unlabeled; stations, transitions, breaks and free rounds are named.
const kindLabel = computed(() => (props.block.kind && props.block.kind !== 'block' ? BLOCK_KIND_LABELS[props.block.kind] : ''))

const tileStyle = computed(() => {
  const color = safeBlockColor(props.block.color)
  return {
    height: `${props.block.duration_minutes * props.minuteHeight}px`,
    top: `${(props.block.start_offset_minutes ?? 0) * props.minuteHeight}px`,
    ...(color ? { '--tile-color': color } : {}),
  }
})
</script>

<style scoped>
/* Tint and border percentages match BLOCK_TINT_PERCENT/BLOCK_BORDER_PERCENT in utils/blockColor.ts */
.block-tile {
  --tile-color: var(--jf-color-primary);
  position: absolute;
  left: var(--jf-space-0-5);
  right: var(--jf-space-0-5);
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid color-mix(in srgb, var(--tile-color) 60%, var(--jf-color-card));
  border-radius: var(--jf-radius-md);
  padding: var(--jf-space-0-5) var(--jf-space-1);
  background: color-mix(in srgb, var(--tile-color) 14%, var(--jf-color-card));
  color: var(--jf-color-text);
  cursor: grab;
  overflow: hidden;
  transition: box-shadow var(--jf-duration), opacity var(--jf-duration);
  user-select: none;
  box-sizing: border-box;
  min-height: 32px;
}
.block-tile.read-only { cursor: pointer; }
.block-tile:hover { box-shadow: var(--jf-shadow-md); }
.block-tile:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.block-tile.selected { outline: 2px solid var(--jf-color-primary); outline-offset: 2px; }
.block-tile.dragging { opacity: 0.7; cursor: grabbing; }

.tile-title {
  font-size: var(--jf-text-sm);
  font-weight: var(--jf-weight-bold);
  line-height: var(--jf-leading-tight);
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  overflow-wrap: anywhere;
}
.tile-meta { font-size: var(--jf-text-xs); line-height: var(--jf-leading-tight); }
.tile-link { margin-right: 0.25rem; font-size: 0.7em; }
/* Actions overlay the tile corner so hidden buttons do not shorten the title */
.tile-actions {
  position: absolute;
  top: 2px;
  right: 2px;
  display: flex;
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-sm);
  opacity: 0;
  pointer-events: none;
  transition: opacity var(--jf-duration);
}
.block-tile:is(:hover, :focus-within) .tile-actions { opacity: 1; pointer-events: auto; }

.resize-handle {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 8px;
  cursor: ns-resize;
  background: linear-gradient(0deg, color-mix(in srgb, var(--tile-color) 40%, transparent) 0%, transparent 100%);
}
.block-tile:not(:hover) .resize-handle { opacity: 0; }
</style>
