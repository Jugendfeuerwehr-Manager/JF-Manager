<template>
  <div class="stats-panel">
    <div class="stats-panel__header" @click="emit('toggle')">
      <span class="stats-panel__title">
        <i class="pi pi-chart-bar"></i>
        Statistiken
        <Tag :value="`${totalMembers} Mitglieder`" severity="secondary" class="ml-2" />
      </span>
      <i :class="['pi', expanded ? 'pi-chevron-up' : 'pi-chevron-down']"></i>
    </div>

    <Transition name="stats-slide">
      <div v-if="expanded" class="stats-panel__content">
        <div v-if="loading" class="stats-loading">
          <i class="pi pi-spin pi-spinner"></i>
          <span>Statistiken werden geladen...</span>
        </div>
        <div v-else-if="stats" class="stats-grid">

          <!-- Gender -->
          <div class="stat-card">
            <div class="stat-card__title">
              <i class="pi pi-users"></i>
              Geschlecht
            </div>
            <div class="stat-bar-group">
              <div v-for="g in genderStats" :key="g.label" class="stat-bar-row">
                <span class="stat-bar-label">{{ g.label }}</span>
                <div class="stat-bar-track">
                  <div
                    class="stat-bar-fill"
                    :style="{ width: stats.total ? `${(g.value / stats.total) * 100}%` : '0%', backgroundColor: g.color }"
                  ></div>
                </div>
                <span class="stat-bar-value">{{ g.value }}</span>
              </div>
            </div>
          </div>

          <!-- Age -->
          <div class="stat-card">
            <div class="stat-card__title">
              <i class="pi pi-calendar"></i>
              Alter
            </div>
            <div v-if="stats.age && stats.age.avg != null" class="age-overview">
              <div class="age-kpis">
                <div class="age-kpi">
                  <span class="age-kpi__value">{{ stats.age.avg }}</span>
                  <span class="age-kpi__label">Ø Jahre</span>
                </div>
                <div class="age-kpi">
                  <span class="age-kpi__value">{{ stats.age.min }}</span>
                  <span class="age-kpi__label">Jüngste/r</span>
                </div>
                <div class="age-kpi">
                  <span class="age-kpi__value">{{ stats.age.max }}</span>
                  <span class="age-kpi__label">Älteste/r</span>
                </div>
              </div>
              <div class="stat-bar-group mt-2">
                <div v-for="bucket in stats.age.buckets" :key="bucket.label" class="stat-bar-row">
                  <span class="stat-bar-label">{{ bucket.label }}</span>
                  <div class="stat-bar-track">
                    <div
                      class="stat-bar-fill"
                      :style="{ width: stats.total ? `${((bucket.count ?? 0) / stats.total) * 100}%` : '0%', backgroundColor: '#4facfe' }"
                    ></div>
                  </div>
                  <span class="stat-bar-value">{{ bucket.count }}</span>
                </div>
              </div>
            </div>
            <p v-else class="stats-empty">Keine Geburtstagsdaten vorhanden</p>
          </div>

          <!-- Status -->
          <div class="stat-card">
            <div class="stat-card__title">
              <i class="pi pi-tag"></i>
              Status
            </div>
            <div class="stat-bar-group">
              <div v-for="s in stats.by_status" :key="s.name" class="stat-bar-row">
                <span class="stat-bar-label">{{ s.name }}</span>
                <div class="stat-bar-track">
                  <div
                    class="stat-bar-fill"
                    :style="{ width: stats.total ? `${(s.count / stats.total) * 100}%` : '0%', backgroundColor: s.color }"
                  ></div>
                </div>
                <span class="stat-bar-value">{{ s.count }}</span>
              </div>
            </div>
          </div>

          <!-- Misc -->
          <div class="stat-card">
            <div class="stat-card__title">
              <i class="pi pi-info-circle"></i>
              Sonstiges
            </div>
            <div class="misc-stats">
              <div class="misc-stat-row">
                <span class="misc-stat-label">
                  <i class="pi pi-check-circle" style="color: #43e97b"></i>
                  Kann schwimmen
                </span>
                <span class="misc-stat-value">
                  {{ stats.can_swim }}
                  <span class="misc-stat-pct">
                    ({{ stats.total ? Math.round((stats.can_swim / stats.total) * 100) : 0 }} %)
                  </span>
                </span>
              </div>
              <div v-for="g in stats.by_group" :key="g.name" class="misc-stat-row">
                <span class="misc-stat-label">
                  <i class="pi pi-users"></i>
                  {{ g.name }}
                </span>
                <span class="misc-stat-value">{{ g.count }}</span>
              </div>
            </div>
          </div>

        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'
import type { MemberStats } from '@/types/members'

interface Props {
  stats: MemberStats | null
  loading: boolean
  expanded: boolean
  totalMembers: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  toggle: []
}>()

const genderStats = computed(() => {
  if (!props.stats) return []
  const g = props.stats.gender
  return [
    { label: 'Männlich', value: g?.male ?? 0, color: '#4facfe' },
    { label: 'Weiblich', value: g?.female ?? 0, color: '#f093fb' },
    { label: 'Divers', value: g?.diverse ?? 0, color: '#43e97b' },
    { label: 'Unbekannt', value: g?.unknown ?? 0, color: '#aaaaaa' },
  ].filter((e) => e.value > 0)
})
</script>

<style scoped>
.stats-panel {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: var(--border-radius);
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.stats-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  cursor: pointer;
  user-select: none;
  transition: background-color 0.15s;
}

.stats-panel__header:hover {
  background: var(--surface-hover);
}

.stats-panel__title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--text-color);
}

.stats-panel__content {
  padding: 1rem 1.25rem 1.25rem;
  border-top: 1px solid var(--surface-border);
}

.stats-loading {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--text-color-secondary);
  padding: 1rem 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1.25rem;
}

.stat-card {
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stat-card__title {
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--text-color-secondary);
  display: flex;
  align-items: center;
  gap: 0.4rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-bar-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.stat-bar-row {
  display: grid;
  grid-template-columns: 90px 1fr 32px;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
}

.stat-bar-label {
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stat-bar-track {
  background: var(--surface-border);
  border-radius: 4px;
  height: 8px;
  overflow: hidden;
}

.stat-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
  min-width: 2px;
}

.stat-bar-value {
  font-weight: 600;
  color: var(--text-color);
  text-align: right;
  font-size: 0.85rem;
}

/* Age KPIs */
.age-overview {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.age-kpis {
  display: flex;
  gap: 1rem;
}

.age-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  background: var(--surface-card);
  border-radius: var(--border-radius);
  padding: 0.5rem;
}

.age-kpi__value {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--primary-color);
  line-height: 1;
}

.age-kpi__label {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  margin-top: 0.2rem;
}

/* Misc stats */
.misc-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.misc-stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9rem;
}

.misc-stat-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-color);
}

.misc-stat-value {
  font-weight: 600;
  color: var(--text-color);
}

.misc-stat-pct {
  font-weight: 400;
  color: var(--text-color-secondary);
  font-size: 0.8rem;
}

.stats-empty {
  color: var(--text-color-secondary);
  font-size: 0.9rem;
  margin: 0;
}

.mt-2 { margin-top: 0.5rem; }
.ml-2 { margin-left: 0.5rem; }

/* Animate stats panel open/close */
.stats-slide-enter-active,
.stats-slide-leave-active {
  transition: max-height 0.3s ease, opacity 0.2s ease;
  max-height: 800px;
  overflow: hidden;
}
.stats-slide-enter-from,
.stats-slide-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
