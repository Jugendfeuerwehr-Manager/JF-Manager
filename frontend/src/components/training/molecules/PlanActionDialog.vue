<template>
  <Dialog :visible="visible" header="Planaktion mit Vorschau" modal :style="{ width: '640px' }" @update:visible="emit('update:visible', $event)">
    <div class="plan-actions">
      <label for="plan-action-kind">Aktion</label>
      <Select input-id="plan-action-kind" v-model="kind" :options="kinds" option-label="label" option-value="value" />
      <label for="plan-action-source">Erster Baustein</label>
      <Select input-id="plan-action-source" v-model="sourceId" :options="planner.blocks" option-label="title" option-value="id" />
      <template v-if="kind === 'swap'">
        <label for="plan-action-target">Tauschen mit</label>
        <Select input-id="plan-action-target" v-model="targetId" :options="planner.blocks.filter((b) => b.id !== sourceId)" option-label="title" option-value="id" />
        <p>Beginn und Gruppen werden getauscht. Inhalte und Dauer bleiben bei ihrem Baustein.</p>
      </template>
      <template v-else>
        <label for="plan-action-delta">Verschiebung in Minuten (negativ = früher)</label>
        <InputNumber input-id="plan-action-delta" v-model="delta" />
        <p>Ab dem ersten Baustein werden alle nachfolgenden Bausteine in seinen Gruppen verschoben. Gemeinsame Bausteine sind eingeschlossen.</p>
      </template>
      <p v-if="preview.error" role="status">{{ preview.error }}</p>
      <table v-else>
        <caption>Vorschau · {{ preview.moves.length }} Bausteine · noch nicht übernommen</caption>
        <thead><tr><th>Baustein</th><th>Beginn (Minute)</th><th>Gruppen</th></tr></thead>
        <tbody><tr v-for="move in preview.moves" :key="move.id">
          <td>{{ move.title }}</td><td>{{ move.from }} → {{ move.to }}</td>
          <td>{{ groupNames(move.fromGroups) }} → {{ groupNames(move.toGroups) }}</td>
        </tr></tbody>
      </table>
      <p>Überlappungen werden durch diese Aktion nicht automatisch aufgelöst. Die Änderungen bleiben bis „Speichern“ im Entwurf.</p>
    </div>
    <template #footer>
      <Button label="Abbrechen" severity="secondary" @click="emit('update:visible', false)" />
      <Button label="Vorschau übernehmen" :disabled="!!preview.error || planner.saving" @click="apply" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import Button from 'primevue/button'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'
import { previewPlanAction } from '../utils/planActions'

const props = defineProps<{ visible: boolean; duration: number }>()
const emit = defineEmits<{ 'update:visible': [visible: boolean] }>()
const planner = useTrainingPlannerStore()
const kind = ref<'swap' | 'shift_following'>('swap')
const sourceId = ref<number | null>(null)
const targetId = ref<number | null>(null)
const delta = ref<number | null>(5)
const kinds = [{ label: 'Tauschen', value: 'swap' }, { label: 'Nachfolgende verschieben', value: 'shift_following' }]
watch(() => props.visible, (visible) => {
  if (visible) { sourceId.value = planner.selectedBlockId; targetId.value = null }
})
const preview = computed(() => {
  try {
    return { error: '', moves: previewPlanAction(planner.blocks, props.duration, kind.value, sourceId.value,
      kind.value === 'swap' ? targetId.value : delta.value) }
  } catch (e) {
    return { error: (e as Error).message, moves: [] }
  }
})
function groupNames(ids: number[]) {
  if (!ids.length) return 'Alle Gruppen'
  const known = [...(planner.session?.groups ?? []), ...planner.blocks.flatMap((b) => b.groups)]
  return ids.map((id) => known.find((g) => g.id === id)?.name ?? `Gruppe ${id}`).join(', ')
}
function apply() {
  if (preview.value.error || planner.saving) return
  planner.beginGesture()
  for (const move of preview.value.moves) planner.stageMove(move.id, move.values)
  planner.endGesture()
  emit('update:visible', false)
}
</script>

<style scoped>
.plan-actions { display: grid; gap: var(--jf-space-2); }
.plan-actions p { margin: 0; }
table { width: 100%; border-collapse: collapse; }
caption { text-align: left; padding: var(--jf-space-1) 0; font-weight: var(--jf-weight-semibold); }
th, td { text-align: left; border-bottom: 1px solid var(--jf-color-border); padding: var(--jf-space-1); }
</style>
