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
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--jf-space-3);
  padding: var(--jf-space-0-5) 0 var(--jf-space-3);
  margin-bottom: var(--jf-space-3);
}

.overview-header__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
}

.overview-header__eyebrow {
  margin: 0;
  font-size: var(--jf-text-xs);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--jf-color-primary);
}

.overview-header__title-row {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1-5);
  flex-wrap: wrap;
}

.overview-header__title {
  margin: 0;
  font-size: clamp(var(--jf-text-xl), 1.2rem + 1vw, var(--jf-text-2xl));
  line-height: var(--jf-leading-tight);
  font-weight: var(--jf-weight-bold);
  letter-spacing: -0.015em;
  color: var(--jf-color-text);
}

.overview-header__subtitle {
  margin: 0;
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-md);
}

.overview-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-1);
  margin-top: var(--jf-space-1);
}

.overview-header__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--jf-space-1);
}

@media (max-width: 768px) {
  .overview-header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--jf-space-2);
    padding-bottom: var(--jf-space-1);
    margin-bottom: var(--jf-space-2);
  }

  .overview-header__actions {
    justify-content: flex-start;
  }
}
</style>
