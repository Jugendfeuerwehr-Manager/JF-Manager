<template>
  <figure class="month-chart">
    <div class="month-chart__plot" role="group" :aria-label="`${label} je Monat`" @mouseleave="active = null">
      <div class="month-chart__grid" aria-hidden="true">
        <span v-for="tick in [100, 50, 0]" :key="tick" class="month-chart__tick" :style="{ bottom: `${tick}%` }">
          <span class="month-chart__tick-label">{{ tick }} %</span>
        </span>
      </div>
      <div class="month-chart__bars" :style="{ gridTemplateColumns: `repeat(${months.length}, minmax(0, 1fr))` }">
        <div
          v-for="(month, index) in months"
          :key="month.month"
          class="month-chart__slot"
          :class="{ 'is-active': active === index, 'is-alternate': index % 2 === 1 }"
          tabindex="0"
          :aria-label="describe(month)"
          @mouseenter="active = index"
          @focus="active = index"
          @blur="active = null"
        >
          <span
            v-if="month.rate !== null"
            class="month-chart__bar"
            :style="{ height: `${Math.max(month.rate, 1)}%` }"
          ></span>
          <span v-else class="month-chart__none" aria-hidden="true">–</span>
          <span class="month-chart__month" aria-hidden="true">{{ formatMonth(month.month) }}</span>
        </div>
      </div>
      <div v-if="activeMonth" class="month-chart__tooltip" :style="tooltipStyle" aria-hidden="true">
        <strong>{{ formatMonth(activeMonth.month, 'long') }}</strong>
        <span class="month-chart__tooltip-rate">{{ formatRate(activeMonth.rate) }}</span>
        <span v-if="activeMonth.recorded" class="month-chart__tooltip-detail">
          {{ activeMonth.present }} anwesend · {{ activeMonth.excused }} entschuldigt · {{ activeMonth.absent }} fehlt
        </span>
        <span v-else class="month-chart__tooltip-detail">Keine Einträge</span>
      </div>
    </div>
    <figcaption class="month-chart__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { formatMonth, formatRate } from '@/utils/reportPeriod'
import type { AttendanceReportGroup } from '@/types/servicebook'

const props = defineProps<{
  months: AttendanceReportGroup['months']
  label: string
  caption: string
}>()

const active = ref<number | null>(null)
const activeMonth = computed(() => (active.value === null ? null : props.months[active.value] ?? null))

// Keep the tooltip inside the plot at both ends.
const tooltipStyle = computed(() => {
  if (active.value === null || !props.months.length) return {}
  const center = ((active.value + 0.5) / props.months.length) * 100
  return { left: `clamp(0px, calc(${center}% - 6.5rem), calc(100% - 13rem))` }
})

function describe(month: AttendanceReportGroup['months'][number]): string {
  const name = formatMonth(month.month, 'long')
  if (!month.recorded) return `${name}: keine Einträge`
  return `${name}: ${formatRate(month.rate)} Teilnahme, ${month.present} anwesend, ${month.excused} entschuldigt, ${month.absent} fehlt`
}
</script>

<style scoped>
.month-chart {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
}

.month-chart__plot {
  position: relative;
  height: 220px;
  padding-left: 2.75rem;
  padding-bottom: 1.75rem;
}

.month-chart__grid {
  position: absolute;
  inset: 0 0 1.75rem 2.75rem;
}

.month-chart__tick {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px solid var(--jf-color-border);
}

.month-chart__tick-label {
  position: absolute;
  right: calc(100% + var(--jf-space-1));
  transform: translateY(-50%);
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
  white-space: nowrap;
}

.month-chart__bars {
  position: relative;
  display: grid;
  height: 100%;
  gap: 2px;
}

.month-chart__slot {
  position: relative;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  height: 100%;
  border-radius: var(--jf-radius-sm, 4px);
  cursor: default;
}

.month-chart__slot:focus-visible {
  outline: 2px solid var(--jf-color-primary);
  outline-offset: 2px;
}

.month-chart__slot.is-active {
  background: var(--jf-color-selected);
}

.month-chart__bar {
  width: min(70%, 2.5rem);
  border-radius: 4px 4px 0 0;
  background: var(--jf-color-primary);
}

.month-chart__none {
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.month-chart__month {
  position: absolute;
  top: calc(100% + var(--jf-space-0-5));
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
  white-space: nowrap;
}

.month-chart__tooltip {
  position: absolute;
  top: 0;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 13rem;
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-md);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text);
  pointer-events: none;
}

.month-chart__tooltip-rate {
  font-size: var(--jf-text-lg);
  font-weight: var(--jf-weight-bold);
}

.month-chart__tooltip-detail,
.month-chart__caption {
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

@media (max-width: 640px) {
  .month-chart__slot.is-alternate .month-chart__month {
    visibility: hidden;
  }
}
</style>
