<template>
  <Dialog
    :visible="visible"
    modal
    header="Teilnahme"
    :style="{ width: '72rem', maxWidth: 'calc(100vw - 24px)' }"
    :content-style="{ paddingTop: 0 }"
    @update:visible="emit('update:visible', $event)"
  >
    <div role="tablist" aria-label="Teilnahme" class="part-tabs" @keydown="onKeydown">
      <button
        v-for="item in tabs"
        :id="`part-tab-${item.key}`"
        :key="item.key"
        type="button"
        role="tab"
        class="part-tabs__tab"
        :aria-selected="tab === item.key"
        :aria-controls="`part-panel-${item.key}`"
        :tabindex="tab === item.key ? 0 : -1"
        @click="tab = item.key"
      >{{ item.label }}</button>
    </div>
    <div v-if="tab === 'settings'" id="part-panel-settings" role="tabpanel" aria-labelledby="part-tab-settings">
      <ParticipationSettings :session-id="sessionId" :readonly="!canManage" />
    </div>
    <div v-else-if="tab === 'registrations'" id="part-panel-registrations" role="tabpanel" aria-labelledby="part-tab-registrations">
      <RegistrationsOverview :session-id="sessionId" :can-manage="canManage" />
    </div>
    <div v-else id="part-panel-assignment" role="tabpanel" aria-labelledby="part-tab-assignment">
      <AssignmentBoard :session-id="sessionId" :can-manage="canManage" />
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import ParticipationSettings from './ParticipationSettings.vue'
import AssignmentBoard from './AssignmentBoard.vue'
import RegistrationsOverview from './RegistrationsOverview.vue'
import { useParticipationStore } from '@/stores/participation'

defineProps<{ visible: boolean, sessionId: number, canManage: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()

const store = useParticipationStore()
type TabKey = 'settings' | 'registrations' | 'assignment'
const tab = ref<TabKey>('settings')
const tabs = computed(() => {
  const list: Array<{ key: TabKey, label: string }> = [
    { key: 'settings', label: 'Teilnahme' },
    { key: 'registrations', label: store.registrations ? `Meldungen · ${store.registrations.counts.seated}` : 'Meldungen' },
  ]
  // PART-04.4: the board belongs to the saved assignment mode
  if (store.config?.mode === 'assignment') list.push({ key: 'assignment', label: 'Zuteilung' })
  return list
})
watch(tabs, list => { if (!list.some(item => item.key === tab.value)) tab.value = 'settings' })

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
  const keys = tabs.value.map(item => item.key)
  const index = keys.indexOf(tab.value)
  tab.value = keys[(index + (event.key === 'ArrowRight' ? 1 : keys.length - 1)) % keys.length]!
  event.preventDefault()
  requestAnimationFrame(() => document.getElementById(`part-tab-${tab.value}`)?.focus())
}
</script>

<style scoped>
.part-tabs { display: flex; gap: var(--jf-space-0-5); margin-bottom: var(--jf-space-2); border-bottom: 1px solid var(--jf-color-border); overflow-x: auto; }
.part-tabs__tab { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-2); border: 0; border-bottom: 3px solid transparent; background: transparent; color: var(--jf-color-text-muted); font: inherit; font-weight: var(--jf-weight-semibold); cursor: pointer; }
.part-tabs__tab[aria-selected='true'] { border-bottom-color: var(--jf-color-primary); color: var(--jf-color-text); }
</style>
