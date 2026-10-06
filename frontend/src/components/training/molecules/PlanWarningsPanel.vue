<template>
  <details class="plan-warnings" :open="planner.warnings.length > 0">
    <summary>
      <StatusBadge
        :label="summary"
        :severity="planner.checkError ? 'danger' : planner.warnings.length ? 'warning' : 'success'"
      />
      <span v-if="planner.checking" class="plan-warnings__muted" role="status">prüft …</span>
    </summary>
    <p class="plan-warnings__muted">
      Planungswarnungen blockieren das Speichern nicht. Veröffentlichen trotz Warnungen verlangt eine Begründung.
    </p>
    <p v-if="planner.checkError" role="alert">{{ planner.checkError }}</p>
    <ul v-if="planner.warnings.length" class="plan-warnings__list">
      <li v-for="(warning, index) in planner.warnings" :key="index">
        <span class="plan-warnings__kind">{{ labels[warning.code] }}</span>
        <span>{{ warning.message }}</span>
        <Button
          v-if="warning.blockIds.length"
          label="Baustein zeigen"
          text
          size="small"
          @click="emit('focus-block', warning.blockIds[0]!)"
        />
      </li>
    </ul>
    <Button label="Erneut prüfen" icon="pi pi-refresh" text size="small" :loading="planner.checking" @click="planner.checkDraft()" />
  </details>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Button from 'primevue/button'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { useTrainingPlannerStore } from '@/stores/trainingPlanner'
import type { PlanWarning } from '@/types/training'

const emit = defineEmits<{ 'focus-block': [id: number] }>()
const planner = useTrainingPlannerStore()

const labels: Record<PlanWarning['code'], string> = {
  group: 'Gruppen',
  instructor: 'Ausbilder',
  location: 'Ort',
  material: 'Material',
}

const summary = computed(() => {
  if (planner.checkError) return 'Prüfung nicht aktuell'
  const count = planner.warnings.length
  return count ? `${count} Planungswarnung${count === 1 ? '' : 'en'}` : 'Keine Planungswarnungen'
})
</script>

<style scoped>
.plan-warnings { margin: 0 0 var(--jf-space-1); padding: var(--jf-space-1) var(--jf-space-2); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); background: var(--jf-color-card); }
.plan-warnings summary { display: flex; align-items: center; gap: var(--jf-space-1); cursor: pointer; }
.plan-warnings p { margin: var(--jf-space-1) 0; }
.plan-warnings__muted { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.plan-warnings__list { display: grid; gap: var(--jf-space-1); margin: var(--jf-space-1) 0; padding: 0; list-style: none; }
.plan-warnings__list li { display: flex; flex-wrap: wrap; align-items: baseline; gap: var(--jf-space-1); }
.plan-warnings__kind { font-weight: var(--jf-weight-semibold); }
</style>
