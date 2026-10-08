<script setup lang="ts">
import { computed, onMounted } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import { usePortalStore } from '@/stores/portal'
import { useAuthStore } from '@/stores/auth'

const portal = usePortalStore()
const auth = useAuthStore()
const firstName = computed(() => portal.me?.account.first_name || auth.user?.first_name || '')
const people = computed(() => portal.me?.people ?? [])

onMounted(() => { void portal.fetchMe() })
</script>

<template>
  <div class="portal-home">
    <h1>Hallo{{ firstName ? ` ${firstName}` : '' }}</h1>

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

    <section v-else aria-labelledby="people-title">
      <h2 id="people-title">Personen</h2>
      <ul class="people">
        <li v-for="person in people" :key="person.id" class="person">
          <i :class="person.relation === 'self' ? 'pi pi-user' : 'pi pi-users'" aria-hidden="true"></i>
          <span>{{ person.relation === 'self' ? 'Ich' : person.first_name }}</span>
        </li>
      </ul>
    </section>

    <div class="hints">
      <RouterLink :to="{ name: 'portal-sessions' }" class="hint">
        <i class="pi pi-calendar" aria-hidden="true"></i>
        <span><strong>Termine</strong><small>An- und Abmeldung zu Diensten</small></span>
      </RouterLink>
      <RouterLink :to="{ name: 'portal-data' }" class="hint">
        <i class="pi pi-id-card" aria-hidden="true"></i>
        <span><strong>Daten</strong><small>Gespeicherte Angaben einsehen</small></span>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.portal-home { display: flex; flex-direction: column; gap: 1rem; }
h1 { margin: 0; font-size: 1.5rem; }
h2 { margin: 0 0 0.5rem; font-size: 1rem; color: var(--p-text-muted-color); }
.state { display: flex; justify-content: center; padding: 2rem; }
.error-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
.empty { margin: 0; padding: 1rem; border: 1px dashed var(--p-content-border-color); border-radius: 0.75rem; color: var(--p-text-muted-color); }
.people { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.person { display: inline-flex; align-items: center; gap: 0.5rem; min-height: 44px; padding: 0 1rem; border-radius: 999px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
.hints { display: grid; gap: 0.75rem; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); }
.hint { display: flex; align-items: center; gap: 0.75rem; min-height: 44px; padding: 1rem; border-radius: 0.75rem; text-decoration: none; color: var(--p-text-color); background: var(--p-content-background); border: 1px solid var(--p-content-border-color); }
.hint i { font-size: 1.25rem; color: var(--p-primary-color); }
.hint span { display: flex; flex-direction: column; }
.hint small { color: var(--p-text-muted-color); }
</style>
