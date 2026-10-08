<template>
  <Dialog :visible="visible" header="Terminserie" modal :style="{ width: '820px', maxWidth: 'calc(100vw - 24px)' }" @update:visible="emit('update:visible', $event)">
    <div class="series-dialog">
      <SegmentedControl v-if="canPropagate" v-model="mode" :options="modes" label="Serienaktion" />
      <SeriesPropagatePanel v-if="mode === 'propagate' && canPropagate" :session-id="sessionId" @propagated="emit('changed')" @navigate="emit('update:visible', false)" />
      <SeriesGeneratePanel v-else :session-id="sessionId" @generated="emit('changed')" @navigate="emit('update:visible', false)" />
    </div>
    <template #footer>
      <Button label="Schließen" severity="secondary" @click="emit('update:visible', false)" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import SeriesGeneratePanel from './SeriesGeneratePanel.vue'
import SeriesPropagatePanel from './SeriesPropagatePanel.vue'

type Mode = 'generate' | 'propagate'

const props = withDefaults(defineProps<{ visible: boolean; sessionId: number | null; canPropagate?: boolean }>(), { canPropagate: false })
const emit = defineEmits<{ 'update:visible': [visible: boolean]; changed: [] }>()

const mode = ref<Mode>('generate')
const modes = [
  { value: 'generate' as Mode, label: 'Fehlende Termine ergänzen' },
  { value: 'propagate' as Mode, label: 'Dieser und folgende' },
]

watch(() => props.visible, (visible) => { if (visible) mode.value = 'generate' })
</script>

<style scoped>
.series-dialog { display: grid; gap: var(--jf-space-3); }
</style>
