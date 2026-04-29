<template>
  <div
    class="member-group-card"
    :class="{ 'is-dragging': isDragging }"
    draggable="true"
    @dragstart.stop="onDragStart"
    @dragend.stop="emit('dragend')"
  >
    <span class="drag-handle" aria-hidden="true">
      <i class="pi pi-bars"></i>
    </span>

    <Avatar
      :image="member.avatar_url ?? undefined"
      :label="initials"
      shape="circle"
      size="small"
      class="member-avatar"
    />

    <div class="member-info">
      <span class="member-name">{{ member.full_name }}</span>
      <Tag
        v-if="member.status"
        :value="member.status.name"
        class="status-tag"
        :style="statusTagStyle"
      />
    </div>

    <!-- Touch / mobile fallback: move-to-group button -->
    <Button
      icon="pi pi-arrows-h"
      text
      rounded
      size="small"
      class="move-btn"
      v-tooltip.top="'Gruppe wechseln'"
      @click.stop="toggleMoveMenu"
    />
    <Menu ref="moveMenuRef" :model="moveMenuItems" popup />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Avatar from 'primevue/avatar'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import Tag from 'primevue/tag'
import type { MenuItem } from 'primevue/menuitem'
import type { Member, Group } from '@/types/members'

interface Props {
  member: Member
  groups: Group[]
  isDragging?: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  dragstart: [event: DragEvent]
  dragend: []
  'move-to-group': [groupId: number | null]
}>()

const moveMenuRef = ref()

const initials = computed(() => {
  const first = props.member.name?.[0] ?? ''
  const last = props.member.lastname?.[0] ?? ''
  return `${first}${last}`.toUpperCase() || '?'
})

const statusTagStyle = computed(() => {
  if (!props.member.status?.color) return {}
  const color = props.member.status.color
  return {
    background: `${color}22`,
    color,
    border: `1px solid ${color}55`,
    fontSize: '0.7rem',
  }
})

const moveMenuItems = computed<MenuItem[]>(() => {
  const items: MenuItem[] = [
    {
      label: 'Ohne Gruppe',
      icon: 'pi pi-ban',
      command: () => emit('move-to-group', null),
    },
    { separator: true },
    ...props.groups.map((g) => ({
      label: g.name,
      icon: 'pi pi-tag',
      disabled: props.member.group?.id === g.id,
      command: () => emit('move-to-group', g.id),
    })),
  ]
  return items
})

function onDragStart(event: DragEvent) {
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', String(props.member.id))
  }
  emit('dragstart', event)
}

function toggleMoveMenu(event: MouseEvent) {
  moveMenuRef.value?.toggle(event)
}
</script>

<style scoped>
.member-group-card {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.625rem;
  border-radius: 8px;
  background: var(--p-surface-0);
  border: 1px solid var(--p-surface-200);
  cursor: grab;
  user-select: none;
  transition:
    box-shadow 0.15s,
    opacity 0.15s,
    transform 0.15s;
}

.member-group-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  border-color: var(--p-primary-300);
}

.member-group-card.is-dragging {
  opacity: 0.45;
  box-shadow: none;
  cursor: grabbing;
}

.drag-handle {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
  flex-shrink: 0;
  cursor: grab;
}

.member-avatar {
  flex-shrink: 0;
}

.member-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.member-name {
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--p-text-color);
}

.status-tag {
  align-self: flex-start;
  font-size: 0.65rem !important;
  padding: 0.1rem 0.4rem !important;
  height: auto !important;
  line-height: 1.4 !important;
}

.move-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.15s;
}

.member-group-card:hover .move-btn {
  opacity: 1;
}

/* Always show move button on touch devices */
@media (hover: none) {
  .move-btn {
    opacity: 1;
  }
}
</style>
