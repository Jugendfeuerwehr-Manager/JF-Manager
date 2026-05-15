<template>
  <div class="settings-layout">
    <!-- Loading State -->
    <div v-if="settingsStore.loading && !settingsStore.canViewAnySettings" class="settings-layout__loading">
      <ProgressSpinner />
    </div>

    <!-- Error State -->
    <Message
      v-else-if="settingsStore.error && !settingsStore.canViewAnySettings"
      severity="error"
      :closable="true"
      @close="settingsStore.clearError()"
    >
      {{ settingsStore.error }}
    </Message>

    <!-- No Permission State -->
    <Message v-else-if="!settingsStore.loading && !settingsStore.canViewAnySettings" severity="warn" :closable="false">
      Sie haben keine Berechtigung, Einstellungen anzuzeigen.
    </Message>

    <!-- Main layout: sidebar + content -->
    <div v-else class="settings-layout__body" :class="{ 'settings-layout__body--mobile': isMobile }">
      <!-- Desktop Sidebar -->
      <aside v-if="!isMobile" class="settings-layout__sidebar">
        <div class="settings-sidebar">
          <div class="settings-sidebar__header">
            <h2 class="settings-sidebar__title">Einstellungen</h2>
          </div>

          <nav class="settings-sidebar__nav">
            <div
              v-for="group in settingsStore.navGroups"
              :key="group.label"
              class="settings-sidebar__group"
            >
              <p class="settings-sidebar__group-label">{{ group.label }}</p>
              <div class="settings-sidebar__items">
                <button
                  v-for="item in group.items"
                  :key="item.id"
                  class="settings-sidebar__item"
                  :class="{ 'settings-sidebar__item--active': activeSection === item.id }"
                  type="button"
                  @click="router.push(`/settings/${item.id}`)"
                >
                  <i :class="item.icon" class="settings-sidebar__item-icon" />
                  <span class="settings-sidebar__item-label">{{ item.title }}</span>
                </button>
              </div>
            </div>
          </nav>
        </div>
      </aside>

      <!-- Content area -->
      <main class="settings-layout__content">
        <router-view v-if="!settingsStore.loading || hasLoadedOnce" />
        <div v-else class="settings-layout__loading">
          <ProgressSpinner />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import ProgressSpinner from 'primevue/progressspinner'
import Message from 'primevue/message'
import { useSettingsStore } from '@/stores/settings'
import { useMobile } from '@/composables/useMobile'

const settingsStore = useSettingsStore()
const toast = useToast()
const router = useRouter()
const route = useRoute()
const { isMobile } = useMobile()

const hasLoadedOnce = ref(false)

const activeSection = computed(() => {
  // Route names are like 'settings-general', 'settings-email', etc.
  const name = route.name as string | undefined
  if (!name) return ''
  return name.replace('settings-', '')
})

onMounted(async () => {
  try {
    await settingsStore.fetchPermissions()

    if (settingsStore.canViewAnySettings) {
      await settingsStore.fetchAllSettings()
    }

    hasLoadedOnce.value = true

    // On desktop, if we're at exactly /settings, redirect to first available section
    if (!isMobile.value && route.name === 'settings-index' && settingsStore.navGroups.length > 0) {
      const firstItem = settingsStore.navGroups[0]?.items[0]
      if (firstItem) {
        router.replace(`/settings/${firstItem.id}`)
      }
    }
  } catch {
    hasLoadedOnce.value = true
    toast.add({
      severity: 'error',
      summary: 'Fehler',
      detail: 'Fehler beim Laden der Einstellungen',
      life: 5000,
    })
  }
})
</script>

<style scoped>
.settings-layout {
  min-height: 100%;
  padding: 2rem;
}

/* On mobile the parent adds no padding, so we keep the layout flush */
@media (max-width: 767px) {
  .settings-layout {
    padding: 0;
  }
}

.settings-layout__loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.settings-layout__body {
  display: flex;
  gap: 0;
  min-height: calc(100vh - 4rem);
  align-items: flex-start;
}

/* Mobile: content fills width */
.settings-layout__body--mobile .settings-layout__content {
  width: 100%;
}

/* ─── Sidebar ───────────────────────────────────────── */
.settings-layout__sidebar {
  width: 240px;
  flex-shrink: 0;
  position: sticky;
  top: 1rem;
  align-self: flex-start;
}

.settings-sidebar {
  background: var(--surface-card);
  border: 1px solid var(--surface-border);
  border-radius: 0.75rem;
  overflow: hidden;
  padding: 0.5rem 0;
}

.settings-sidebar__header {
  padding: 0.75rem 1rem 0.5rem;
  border-bottom: 1px solid var(--surface-border);
  margin-bottom: 0.5rem;
}

.settings-sidebar__title {
  font-size: 1rem;
  font-weight: 600;
  margin: 0;
  color: var(--text-color);
}

.settings-sidebar__nav {
  padding: 0 0.375rem;
}

.settings-sidebar__group {
  margin-bottom: 0.75rem;
}

.settings-sidebar__group:last-child {
  margin-bottom: 0.25rem;
}

.settings-sidebar__group-label {
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-color-secondary);
  margin: 0 0 0.25rem;
  padding: 0 0.625rem;
}

.settings-sidebar__items {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.settings-sidebar__item {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  padding: 0.5rem 0.625rem;
  border-radius: 0.5rem;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  color: var(--text-color);
  font-size: 0.875rem;
  transition: background 0.15s;
}

.settings-sidebar__item:hover {
  background: var(--surface-hover);
}

.settings-sidebar__item--active {
  background: var(--highlight-bg, color-mix(in srgb, var(--primary-color) 12%, transparent));
  color: var(--primary-color);
  font-weight: 500;
}

.settings-sidebar__item-icon {
  font-size: 0.875rem;
  width: 1rem;
  flex-shrink: 0;
}

/* ─── Content ───────────────────────────────────────── */
.settings-layout__content {
  flex: 1;
  min-width: 0;
  padding: 0 0 2rem 1.5rem;
}

/* Remove left padding on mobile */
.settings-layout__body--mobile .settings-layout__content {
  padding-left: 0;
}
</style>
