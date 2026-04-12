<template>
  <div class="attendance-stats">
    <div class="stat-item stat-present" title="Anwesend">
      <i class="pi pi-check"></i>
      <span class="stat-value">{{ summary.present }}</span>
    </div>
    <div class="stat-item stat-excused" title="Entschuldigt">
      <i class="pi pi-exclamation-triangle"></i>
      <span class="stat-value">{{ summary.excused }}</span>
    </div>
    <div class="stat-item stat-absent" title="Fehlend">
      <i class="pi pi-times"></i>
      <span class="stat-value">{{ summary.absent }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { AttendanceSummary } from '@/types/servicebook'

interface Props {
  summary: AttendanceSummary
}

defineProps<Props>()
</script>

<style scoped>
.attendance-stats {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.45rem;
  border-radius: var(--border-radius);
  background: var(--surface-50);
}

.stat-item i {
  font-size: 0.9rem;
}

.stat-present {
  color: var(--green-600);
  background: var(--green-50);
}

.stat-excused {
  color: var(--yellow-600);
  background: var(--yellow-50);
}

.stat-absent {
  color: var(--red-600);
  background: var(--red-50);
}

.stat-value {
  font-size: 0.95rem;
  font-weight: 600;
}

@media (max-width: 576px) {
  .attendance-stats {
    gap: 0.3rem;
    justify-content: flex-end;
  }

  .stat-item {
    padding: 0.2rem 0.35rem;
    flex-direction: column;
    align-items: flex-start;
  }

  .stat-value {
    font-size: 0.85rem;
  }
}
</style>
