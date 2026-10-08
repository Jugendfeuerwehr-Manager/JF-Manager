<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import PortalEmptyCard from '@/components/portal/PortalEmptyCard.vue'
import { usePortalStore } from '@/stores/portal'

const portal = usePortalStore()
const people = computed(() => portal.me?.people ?? [])
const forName = computed(() => {
  const person = portal.selectedPerson
  return person ? (person.relation === 'self' ? 'dich' : person.first_name) : ''
})

onMounted(() => { void portal.fetchMe() })
</script>

<template>
  <div class="portal-home">
    <div v-if="portal.loading && !portal.me" class="state" role="status">
      <ProgressSpinner style="width: 2rem; height: 2rem" aria-label="Wird geladen" />
    </div>

    <Message v-else-if="portal.error" severity="error" :closable="false">
      <div class="error-row">
        <span>{{ portal.error }}</span>
        <Button label="Erneut versuchen" size="small" severity="secondary" @click="portal.fetchMe()" />
      </div>
    </Message>

    <p v-else-if="!people.length" class="empty">
      Noch keine Person mit diesem Zugang verknüpft. Bitte wende dich an die Jugendfeuerwehr.
    </p>

    <template v-else>
      <div class="heading">
        <h1>Nächste Dienste</h1>
        <span v-if="forName" class="for">für {{ forName }}</span>
      </div>
      <PortalEmptyCard icon="pi pi-calendar" title="Noch keine geplanten Dienste">
        Sobald Dienste veröffentlicht sind, kannst du hier an- und abmelden.
      </PortalEmptyCard>
    </template>
  </div>
</template>

<style scoped>
.portal-home { display: flex; flex-direction: column; gap: 12px; }
.heading { display: flex; align-items: baseline; justify-content: space-between; margin-top: 4px; }
h1 { margin: 0; font-size: 18px; font-weight: 700; }
.for { font-size: 13px; color: var(--p-text-muted-color); }
.state { display: flex; justify-content: center; padding: 2rem; }
.error-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
.empty { margin: 0; padding: 14px; border: 1px dashed var(--p-content-border-color); border-radius: 14px; color: var(--p-text-muted-color); }
</style>
