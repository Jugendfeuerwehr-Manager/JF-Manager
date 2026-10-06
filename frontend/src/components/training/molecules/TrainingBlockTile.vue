<template>
  <div class="block-tile"
    :data-block-id="block.id"
    tabindex="0"
    role="group"
    :aria-label="`${block.title}, ab Minute ${block.start_offset_minutes}, ${block.duration_minutes} Minuten. ${readOnly ? 'Enter: Details ansehen.' : 'Enter: bearbeiten. Pfeiltasten auf/ab: verschieben, mit Alt: Dauer ändern.'}`"
    @keydown="onKeydown"
    :style="tileStyle"
    :class="{ selected: selected, dragging: isDragging }"
    @click.stop="emit('click', block)"
  >
    <div class="tile-header">
      <span class="tile-title">{{ block.title }}</span>
      <div v-if="!readOnly" class="tile-actions">
        <Button icon="pi pi-pencil" text size="small" :aria-label="`${block.title} bearbeiten`" @click.stop="emit('edit', block)" />
        <Button icon="pi pi-trash" text size="small" severity="danger" :aria-label="`${block.title} entfernen`" @click.stop="emit('remove', block.id)" />
      </div>
    </div>
    <div class="tile-duration">
      <BlockDurationBadge :minutes="block.duration_minutes" />
    </div>
    <div v-if="!readOnly" class="resize-handle" title="Dauer ändern" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Button from 'primevue/button'
import BlockDurationBadge from '../atoms/BlockDurationBadge.vue'
import type { PlannerBlock, TrainingBlockMove } from '@/types/training'

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

const tileStyle = computed(() => ({
  height: `${props.block.duration_minutes * props.minuteHeight}px`,
  top: `${(props.block.start_offset_minutes ?? 0) * props.minuteHeight}px`,
  backgroundColor: props.block.color ? `${props.block.color}33` : 'var(--primary-50, #eff6ff)',
  borderColor: props.block.color ?? 'var(--primary-color)',
}))
</script>

<style scoped>
.block-tile {
  position: absolute;
  left: 4px;
  right: 4px;
  border: 2px solid var(--primary-color);
  border-radius: 6px;
  padding: 0.375rem 0.5rem;
  background: var(--primary-50, #eff6ff);
  cursor: grab;
  overflow: hidden;
  transition: box-shadow 0.1s, opacity 0.1s;
  user-select: none;
  box-sizing: border-box;
  min-height: 32px;
}
.block-tile:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
.block-tile.selected { box-shadow: 0 0 0 3px var(--primary-color); }
.block-tile.dragging { opacity: 0.7; cursor: grabbing; }

.tile-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.25rem;
}
.tile-title {
  font-size: 0.8rem;
  font-weight: 600;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tile-actions { display: flex; gap: 0; opacity: 0; transition: opacity 0.1s; }
.block-tile:is(:hover, :focus-within) .tile-actions { opacity: 1; }
.tile-duration { margin-top: 2px; }

.resize-handle {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 8px;
  cursor: ns-resize;
  background: linear-gradient(0deg, rgba(0,0,0,0.15) 0%, transparent 100%);
  border-radius: 0 0 4px 4px;
}
.block-tile:not(:hover) .resize-handle { opacity: 0; }
</style>
