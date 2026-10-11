<template>
  <section class="own-entry" aria-labelledby="own-entry-title">
    <header class="own-entry__head">
      <h2 id="own-entry-title"><i class="pi pi-user" aria-hidden="true"></i>Mein Bereich</h2>
      <router-link :to="auth.linkedPerson.member ? '/ich/dienste' : '/ich/kinder'" class="own-entry__link">Öffnen<i class="pi pi-arrow-right" aria-hidden="true"></i></router-link>
    </header>
    <template v-if="auth.linkedPerson.member">
      <p v-if="portal.sessionsLoading && !next" class="muted" role="status">Dienste werden geladen …</p>
      <p v-else-if="!next" class="muted">Keine anstehenden Dienste für dich.</p>
      <router-link v-else :to="'/ich/dienste'" class="own-entry__session">
        <span class="own-entry__title">{{ next.title }}</span>
        <span class="muted">{{ when(next) }}</span>
        <StatusBadge :label="stateLabel(next.state)" :severity="stateSeverity(next.state)" :icon="stateIcon(next.state)" />
      </router-link>
    </template>
    <nav class="own-entry__links" aria-label="Mein Bereich">
      <router-link v-if="auth.linkedPerson.member" to="/ich/daten">Meine Daten</router-link>
      <router-link v-if="auth.linkedPerson.children" to="/ich/kinder">Meine Kinder</router-link>
    </nav>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import StatusBadge, { type StatusSeverity } from '@/components/common/StatusBadge.vue'
import type { PortalRegistrationState, PortalSessionItem } from '@/api/portal'
import { useAuthStore } from '@/stores/auth'
import { usePortalStore } from '@/stores/portal'

const auth = useAuthStore()
const portal = usePortalStore()
const selfId = computed(() => portal.me?.people.find(p => p.relation === 'self')?.id ?? null)
const next = computed(() => (portal.sessionsPersonId === selfId.value ? portal.sessions.find(s => s.session_status === 'published') ?? null : null))

onMounted(async () => {
  if (!auth.linkedPerson.member) return
  portal.useOwnArea()
  if (!portal.me) await portal.fetchMe()
  if (selfId.value !== null) {
    portal.selectPerson(selfId.value)
    await portal.loadSessions(selfId.value)
  }
})

const dayFormat = new Intl.DateTimeFormat('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit' })
function when(item: PortalSessionItem) {
  const day = dayFormat.format(new Date(`${item.date}T00:00:00`))
  return item.start_time ? `${day}, ${item.start_time.slice(0, 5)} Uhr` : day
}
const LABELS: Partial<Record<PortalRegistrationState, [string, StatusSeverity, string]>> = {
  expected: ['Erwartet', 'info', 'pi pi-clock'],
  registered: ['Angemeldet', 'success', 'pi pi-check-circle'],
  assigned: ['Zugeteilt', 'success', 'pi pi-check-circle'],
  cancelled: ['Abgemeldet', 'neutral', 'pi pi-times-circle'],
  waitlisted: ['Warteliste', 'warning', 'pi pi-hourglass'],
  applied: ['Beworben', 'info', 'pi pi-send'],
  not_selected: ['Nicht berücksichtigt', 'neutral', 'pi pi-minus-circle'],
  no_response: ['Keine Rückmeldung', 'warning', 'pi pi-question-circle'],
}
const stateLabel = (s: PortalRegistrationState) => LABELS[s]?.[0] ?? s
const stateSeverity = (s: PortalRegistrationState) => LABELS[s]?.[1] ?? 'neutral'
const stateIcon = (s: PortalRegistrationState) => LABELS[s]?.[2] ?? 'pi pi-circle'
</script>

<style scoped>
.own-entry { display: flex; flex-direction: column; gap: var(--jf-space-1-5); padding: var(--jf-space-2); background: var(--jf-color-card); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); }
.own-entry__head { display: flex; align-items: center; justify-content: space-between; gap: var(--jf-space-1); }
h2 { display: flex; align-items: center; gap: var(--jf-space-1); margin: 0; font-size: var(--jf-text-md); font-weight: var(--jf-weight-semibold); }
h2 i { color: var(--jf-color-text-muted); }
a { color: var(--jf-color-primary); font-weight: var(--jf-weight-semibold); font-size: var(--jf-text-sm); text-decoration: none; }
a:focus-visible { outline: var(--jf-focus-ring); outline-offset: 2px; }
.own-entry__link { display: inline-flex; align-items: center; gap: var(--jf-space-0-5); min-height: var(--jf-touch-target); }
.own-entry__session { display: flex; flex-wrap: wrap; align-items: center; gap: var(--jf-space-0-5) var(--jf-space-1-5); min-height: var(--jf-touch-target); padding: var(--jf-space-1) var(--jf-space-1-5); border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-md); color: var(--jf-color-text); }
.own-entry__title { font-weight: var(--jf-weight-semibold); }
.own-entry__links { display: flex; flex-wrap: wrap; gap: var(--jf-space-2); }
.own-entry__links a { display: inline-flex; align-items: center; min-height: var(--jf-touch-target); }
.muted { margin: 0; color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); font-weight: var(--jf-weight-medium); }
</style>
