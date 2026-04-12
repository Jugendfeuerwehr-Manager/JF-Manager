<template>
  <section class="overview-header">
    <div class="overview-header__info">
      <p v-if="eyebrowText" class="overview-header__eyebrow">{{ eyebrowText }}</p>
      <div class="overview-header__title-row">
        <h1 class="overview-header__title">{{ title }}</h1>
        <slot name="badge" />
      </div>
      <p v-if="subtitle" class="overview-header__subtitle">{{ subtitle }}</p>
      <div v-if="hasMeta" class="overview-header__meta">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="hasActions" class="overview-header__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'

interface Props {
  title: string
  subtitle?: string
  eyebrow?: string
}

const props = defineProps<Props>()
const slots = useSlots()

const hasMeta = computed(() => Boolean(slots.meta))
const hasActions = computed(() => Boolean(slots.actions))

const eyebrowText = computed(() => props.eyebrow?.toUpperCase())
</script>

<style scoped>
.overview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 0.25rem 0 1.5rem;
  border-bottom: 1px solid var(--surface-border);
  margin-bottom: 1.5rem;
}

.overview-header__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.overview-header__eyebrow {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-color-secondary);
}

.overview-header__title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.overview-header__title {
  margin: 0;
  font-size: clamp(1.75rem, 1.4rem + 1vw, 2.25rem);
  font-weight: 700;
  color: var(--text-color);
}

.overview-header__subtitle {
  margin: 0;
  color: var(--text-color-secondary);
  font-size: 1rem;
}

.overview-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.overview-header__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  min-width: 220px;
}

@media (max-width: 768px) {
  .overview-header {
    flex-direction: column;
    gap: 1rem;
    border-bottom: none;
    padding-bottom: 1rem;
    margin-bottom: 1rem;
  }

  .overview-header__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
