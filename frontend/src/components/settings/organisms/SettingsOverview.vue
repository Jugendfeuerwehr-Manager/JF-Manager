<template>
  <div class="settings-overview">
    <div class="settings-overview__header">
      <h1 class="settings-overview__title">Einstellungen</h1>
      <p class="settings-overview__subtitle">Verwalten Sie die Anwendungseinstellungen</p>
    </div>

    <div
      v-for="group in settingsStore.navGroups"
      :key="group.label"
      class="settings-overview__group"
    >
      <p class="settings-overview__group-label">{{ group.label }}</p>
      <div class="settings-overview__items">
        <button
          v-for="item in group.items"
          :key="item.id"
          class="settings-overview__item"
          type="button"
          @click="router.push(`/settings/${item.id}`)"
        >
          <div class="settings-overview__item-icon">
            <i :class="item.icon" />
          </div>
          <div class="settings-overview__item-text">
            <span class="settings-overview__item-title">{{ item.title }}</span>
            <span class="settings-overview__item-description">{{ item.description }}</span>
          </div>
          <i class="pi pi-chevron-right settings-overview__item-chevron" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { useMobile } from '@/composables/useMobile'

const settingsStore = useSettingsStore()
const router = useRouter()
const { isMobile } = useMobile()

onMounted(() => {
  // On desktop, redirect to first available section immediately
  if (!isMobile.value && settingsStore.navGroups.length > 0) {
    const firstItem = settingsStore.navGroups[0]?.items[0]
    if (firstItem) {
      router.replace(`/settings/${firstItem.id}`)
    }
  }
})
</script>

<style scoped>
.settings-overview {
  padding: 1.5rem 1rem;
  max-width: 640px;
}

.settings-overview__header {
  margin-bottom: 1.5rem;
}

.settings-overview__title {
  font-size: 1.75rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
}

.settings-overview__subtitle {
  color: var(--text-color-secondary);
  margin: 0;
  font-size: 0.95rem;
}

.settings-overview__group {
  margin-bottom: 1.5rem;
}

.settings-overview__group-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-color-secondary);
  margin: 0 0 0.5rem;
  padding: 0 0.25rem;
}

.settings-overview__items {
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--surface-border);
  background: var(--surface-card);
}

.settings-overview__item {
  display: flex;
  align-items: center;
  gap: 0.875rem;
  width: 100%;
  padding: 0.875rem 1rem;
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--surface-border);
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
  color: var(--text-color);
}

.settings-overview__item:last-child {
  border-bottom: none;
}

.settings-overview__item:hover {
  background: var(--surface-hover);
}

.settings-overview__item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.5rem;
  background: var(--primary-100, color-mix(in srgb, var(--primary-color) 15%, transparent));
  color: var(--primary-color);
  flex-shrink: 0;
  font-size: 1rem;
}

.settings-overview__item-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.settings-overview__item-title {
  font-size: 0.9375rem;
  font-weight: 500;
}

.settings-overview__item-description {
  font-size: 0.8125rem;
  color: var(--text-color-secondary);
}

.settings-overview__item-chevron {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  flex-shrink: 0;
}
</style>
