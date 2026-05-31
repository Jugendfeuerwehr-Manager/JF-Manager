<template>
  <div class="attendance-tab">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <ProgressSpinner style="width: 50px; height: 50px" />
    </div>

    <!-- Empty State -->
    <div v-else-if="!attendances.length" class="empty-state">
      <i class="pi pi-calendar" style="font-size: 3rem; color: var(--text-color-secondary)"></i>
      <p>Noch keine Einträge vorhanden</p>
    </div>

    <!-- Summary Stats -->
    <div v-else class="attendance-container">
      <div class="compact-header">
        <h3 class="m-0">Anwesenheitsverlauf</h3>
        <Tag
          v-if="attendanceRate !== null"
          :value="`${attendanceRate}%`"
          :severity="getAttendanceRateSeverity()"
          icon="pi pi-chart-line"
        />
      </div>

      <div class="stats-row">
        <div class="stat-pill stat-pill-a">A: {{ summary.present }}</div>
        <div class="stat-pill stat-pill-e">E: {{ summary.excused }}</div>
        <div class="stat-pill stat-pill-f">F: {{ summary.absent }}</div>
        <div class="stat-pill stat-pill-total">Gesamt: {{ summary.total }}</div>
      </div>

      <div class="attendance-items">
        <div
          v-for="record in attendances"
          :key="record.id"
          class="attendance-item"
          :class="`state-${record.state}`"
        >
          <div class="state-letter" :class="`status-${record.state}`">{{ record.state || '-' }}</div>

          <div class="item-main">
            <div class="item-topline">
              <span class="date-label">{{ formatDate(record.service_date) }}</span>
              <span class="day-label">{{ getDayName(record.service_date) }}</span>
              <span class="state-label">{{ record.state_display }}</span>
            </div>
            <div class="topic" :title="record.service_topic || 'Kein Thema'">
              {{ record.service_topic || 'Kein Thema' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Load More Button -->
      <div v-if="hasMore" class="load-more-container">
        <Button
          label="Weitere Einträge"
          text
          icon="pi pi-chevron-down"
          size="small"
          @click="loadMore"
          :loading="loadingMore"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { servicebookApi } from '@/api/servicebook'
import type { Attendance, AttendanceSummary, MemberAttendanceParams } from '@/types/servicebook'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressSpinner from 'primevue/progressspinner'

interface Props {
  memberId: number
}

const props = defineProps<Props>()
const toast = useToast()

const attendances = ref<Attendance[]>([])
const summary = ref<AttendanceSummary>({
  present: 0,
  excused: 0,
  absent: 0,
  total: 0
})
const loading = ref(false)
const loadingMore = ref(false)
const limit = ref(50)
const hasMore = ref(false)

const attendanceRate = computed(() => {
  if (summary.value.total === 0) return null
  const rate = Math.round((summary.value.present / summary.value.total) * 100)
  return rate
})

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleDateString('de-DE', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
}

const getDayName = (dateString: string): string => {
  const date = new Date(dateString)
  const days: string[] = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']
  return days[date.getDay()] || 'So'
}

const getAttendanceRateSeverity = (): string => {
  if (!attendanceRate.value) return 'info'
  if (attendanceRate.value >= 80) return 'success'
  if (attendanceRate.value >= 60) return 'warning'
  return 'danger'
}

const loadAttendance = async () => {
  loading.value = true
  try {
    const params: MemberAttendanceParams = {
      member_id: props.memberId,
      limit: limit.value
    }
    const response = await servicebookApi.attendance.getByMember(params)
    attendances.value = response.data.attendances
    summary.value = response.data.summary
    
    // Check if there are more records (API returns limited results)
    hasMore.value = attendances.value.length === limit.value
  } catch (_error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Einträge konnten nicht geladen werden',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

const loadMore = async () => {
  loadingMore.value = true
  try {
    const params: MemberAttendanceParams = {
      member_id: props.memberId,
      limit: limit.value + 25
    }
    const response = await servicebookApi.attendance.getByMember(params)
    attendances.value = response.data.attendances
    summary.value = response.data.summary
    
    hasMore.value = attendances.value.length === (limit.value + 25)
    limit.value += 25
  } catch (_error) {
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Weitere Einträge konnten nicht geladen werden',
      life: 3000
    })
  } finally {
    loadingMore.value = false
  }
}

onMounted(() => {
  loadAttendance()
})
</script>

<style scoped>
.attendance-tab {
  width: 100%;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 3rem;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  text-align: center;
  color: var(--text-color-secondary);
}

.empty-state i {
  margin-bottom: 1rem;
}

.attendance-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.compact-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.attendance-items {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.stat-pill {
  padding: 0.25rem 0.5rem;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.2;
  border: 1px solid transparent;
}

.stat-pill-a {
  color: var(--green-700);
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
}

.stat-pill-e {
  color: var(--yellow-800);
  background: rgba(234, 179, 8, 0.12);
  border-color: rgba(234, 179, 8, 0.35);
}

.stat-pill-f {
  color: var(--red-700);
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.stat-pill-total {
  color: var(--text-color-secondary);
  background: var(--surface-100);
  border-color: var(--surface-border);
}

.attendance-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0.55rem;
  border-radius: var(--border-radius);
  border-left: 3px solid transparent;
  background-color: var(--surface-50);
  min-height: 44px;
}

.attendance-item:hover {
  background-color: var(--surface-100);
}

.state-letter {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  border: 1px solid transparent;
  flex-shrink: 0;
}

.attendance-item.state-A {
  border-left-color: var(--green-500);
}

.attendance-item.state-E {
  border-left-color: var(--yellow-500);
}

.attendance-item.state-F {
  border-left-color: var(--red-500);
}

.date-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-color-secondary);
}

.day-label {
  font-size: 0.78rem;
  color: var(--text-color);
  background: var(--surface-100);
  border-radius: 999px;
  padding: 0.05rem 0.35rem;
}

.item-main {
  flex: 1;
  min-width: 0;
}

.item-topline {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.1rem;
}

.topic {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9rem;
  font-weight: 500;
  color: var(--text-color);
}

.state-label {
  margin-left: auto;
  font-size: 0.75rem;
}

.status-A {
  color: var(--green-700);
  background: rgba(34, 197, 94, 0.1);
  border-color: rgba(34, 197, 94, 0.3);
}

.status-E {
  color: var(--yellow-800);
  background: rgba(234, 179, 8, 0.12);
  border-color: rgba(234, 179, 8, 0.35);
}

.status-F {
  color: var(--red-700);
  background: rgba(239, 68, 68, 0.1);
  border-color: rgba(239, 68, 68, 0.3);
}

.status-null {
  color: var(--text-color-secondary);
  background: var(--surface-100);
  border-color: var(--surface-border);
}

.topic:empty,
.state-label,
.topic-empty {
  color: var(--text-color-secondary);
}

.load-more-container {
  display: flex;
  justify-content: center;
  padding-top: 0.2rem;
  border-top: 1px solid var(--surface-border);
  margin-top: 0.35rem;
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .attendance-container {
    gap: 0.6rem;
  }

  .attendance-item {
    padding: 0.45rem;
  }

  .state-label {
    display: none;
  }
}
</style>
