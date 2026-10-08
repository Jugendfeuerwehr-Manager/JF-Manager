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
    <div v-else id="part-panel-registrations" role="tabpanel" aria-labelledby="part-tab-registrations">
      <RegistrationsOverview :session-id="sessionId" :can-manage="canManage" />
    </div>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Dialog from 'primevue/dialog'
import ParticipationSettings from './ParticipationSettings.vue'
import RegistrationsOverview from './RegistrationsOverview.vue'
import { useParticipationStore } from '@/stores/participation'

defineProps<{ visible: boolean, sessionId: number, canManage: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()

const store = useParticipationStore()
const tab = ref<'settings' | 'registrations'>('settings')
const tabs = computed(() => [
  { key: 'settings' as const, label: 'Teilnahme' },
  { key: 'registrations' as const, label: store.registrations ? `Meldungen · ${store.registrations.counts.seated}` : 'Meldungen' },
])

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
  tab.value = tab.value === 'settings' ? 'registrations' : 'settings'
  event.preventDefault()
  requestAnimationFrame(() => document.getElementById(`part-tab-${tab.value}`)?.focus())
}
</script>

<style scoped>
.part-tabs { display: flex; gap: var(--jf-space-0-5); margin-bottom: var(--jf-space-2); border-bottom: 1px solid var(--jf-color-border); overflow-x: auto; }
.part-tabs__tab { min-height: var(--jf-touch-target); padding: 0 var(--jf-space-2); border: 0; border-bottom: 3px solid transparent; background: transparent; color: var(--jf-color-text-muted); font: inherit; font-weight: var(--jf-weight-semibold); cursor: pointer; }
.part-tabs__tab[aria-selected='true'] { border-bottom-color: var(--jf-color-primary); color: var(--jf-color-text); }
</style>
