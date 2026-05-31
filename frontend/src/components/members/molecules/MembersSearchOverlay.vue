<template>
  <div class="members-search-overlay">
    <div class="members-search-overlay__top">
      <Button
        icon="pi pi-arrow-left"
        text
        rounded
        aria-label="Suche schließen"
        class="members-search-overlay__back"
        @click="emit('close')"
      />

      <IconField class="members-search-overlay__field">
        <InputIcon class="pi pi-search" />
        <InputText
          ref="inputRef"
          v-model="localSearch"
          placeholder="Mitglied suchen..."
          class="w-full"
          @input="emit('update:search', localSearch); emit('search-change')"
          @keydown.esc="emit('close')"
        />
      </IconField>
    </div>

    <div class="members-search-overlay__results">
      <div v-if="!localSearch.trim()" class="mobile-search-state">
        <i class="pi pi-search"></i>
        <p>Tippe einen Namen, um Mitglieder zu finden.</p>
      </div>

      <div v-else-if="loading" class="mobile-search-state">
        <i class="pi pi-spin pi-spinner"></i>
        <p>Suche läuft...</p>
      </div>

      <div v-else-if="members.length" class="mobile-search-results">
        <button
          v-for="member in members"
          :key="member.id"
          type="button"
          class="mobile-search-row"
          @click="emit('select', member)"
        >
          <Avatar
            v-if="member.avatar_url"
            :image="member.avatar_url"
            shape="circle"
            class="mobile-search-row__avatar"
          />
          <Avatar
            v-else
            :label="memberInitials(member)"
            shape="circle"
            class="mobile-search-row__avatar"
          />

          <div class="mobile-search-row__content">
            <span class="mobile-search-row__name">{{ member.full_name }}</span>
            <span class="mobile-search-row__meta">{{ memberGroupsLabel(member) }}</span>
          </div>

          <i class="pi pi-chevron-right mobile-search-row__chevron"></i>
        </button>
      </div>

      <div v-else class="mobile-search-state">
        <i class="pi pi-users"></i>
        <p>Keine Treffer gefunden.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Avatar from 'primevue/avatar'
import type { Member } from '@/types/members'
import type { Department } from '@/types/departments'

interface Props {
  search: string
  members: Member[]
  loading: boolean
  departments?: Department[]
}

const props = withDefaults(defineProps<Props>(), { departments: () => [] })

const emit = defineEmits<{
  close: []
  select: [member: Member]
  'update:search': [value: string]
  'search-change': []
}>()

const inputRef = ref<HTMLInputElement | null>(null)
const localSearch = ref(props.search)

watch(() => props.search, (v) => { localSearch.value = v })

defineExpose({ inputRef })

function memberInitials(member: Member) {
  const first = member.name?.[0] || ''
  const last = member.lastname?.[0] || ''
  const fallback = member.full_name?.[0] || ''
  return `${first}${last}`.trim().toUpperCase() || fallback.toUpperCase()
}

function memberGroupsLabel(member: Member): string {
  const labels: string[] = []
  if (member.group?.name) labels.push(member.group.name)
  if (member.department_ids?.length) {
    for (const deptId of member.department_ids) {
      const name = props.departments.find((d) => d.id === deptId)?.name
      if (name && !labels.includes(name)) labels.push(name)
    }
  }
  return labels.join(' · ') || 'Keine Gruppe'
}
</script>

<style scoped>
.members-search-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background-color: var(--p-content-background, #ffffff);
  display: flex;
  flex-direction: column;
}

.members-search-overlay__top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: calc(env(safe-area-inset-top) + 0.5rem) 0.9rem 0.6rem;
  border-bottom: 1px solid var(--surface-border);
  background: var(--surface-card);
}

.members-search-overlay__back {
  flex-shrink: 0;
}

.members-search-overlay__field {
  flex: 1;
}

.members-search-overlay__results {
  flex: 1;
  overflow-y: auto;
  padding: 0.65rem 0.75rem calc(env(safe-area-inset-bottom) + 0.8rem);
  -webkit-overflow-scrolling: touch;
}

.mobile-search-results {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.mobile-search-row {
  width: 100%;
  border: 1px solid var(--surface-border);
  background: var(--surface-card);
  border-radius: calc(var(--border-radius) - 2px);
  display: flex;
  align-items: center;
  gap: 0.55rem;
  text-align: left;
  padding: 0.45rem 0.6rem;
  cursor: pointer;
}

.mobile-search-row__avatar {
  width: 2rem;
  height: 2rem;
  min-width: 2rem;
}

.mobile-search-row__content {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.mobile-search-row__name {
  font-weight: 600;
  line-height: 1.2;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mobile-search-row__meta {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mobile-search-row__chevron {
  color: var(--text-color-secondary);
  font-size: 0.85rem;
}

.mobile-search-state {
  border: 1px dashed var(--surface-border);
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 1.25rem 0.75rem;
  text-align: center;
}

.mobile-search-state p {
  margin: 0;
  font-size: 0.9rem;
}
</style>
