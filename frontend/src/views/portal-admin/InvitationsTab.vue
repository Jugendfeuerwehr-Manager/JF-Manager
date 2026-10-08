<template>
  <section aria-label="Einladungen">
    <StateView v-if="store.invitationsLoading && !store.invitations.length" kind="loading" />
    <StateView v-else-if="store.invitationsError" kind="error" :message="store.invitationsError" @retry="store.loadInvitations()" />
    <StateView v-else-if="!store.invitations.length" kind="empty" title="Keine Einladungen" message="Es wurde noch keine Einladung verschickt." />
    <ul v-else class="rows">
      <li v-for="inv in store.invitations" :key="inv.id" class="row">
        <div class="row__main">
          <strong>{{ inv.person_name }}</strong>
          <span class="meta">{{ inv.email }}</span>
          <span class="meta">Erstellt {{ formatDate(inv.created_at, true) }} von {{ inv.created_by_name }} · gültig bis {{ formatDate(inv.expires_at) }}</span>
        </div>
        <StatusBadge :label="invitationStateMeta[inv.state].label" :severity="invitationStateMeta[inv.state].severity" :icon="invitationStateMeta[inv.state].icon" />
        <div v-if="inv.state === 'open' || inv.state === 'expired'" class="row__actions">
          <Button label="Erneut senden" icon="pi pi-refresh" size="small" :disabled="store.busy" @click="actions.forInvitation(inv, 'resend')" />
          <Button v-if="inv.state === 'open'" label="Widerrufen" icon="pi pi-times" size="small" severity="secondary" outlined :disabled="store.busy" @click="actions.forInvitation(inv, 'revoke')" />
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import Button from 'primevue/button'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { usePortalAdminStore } from '@/stores/portalAdmin'
import { formatDate, invitationStateMeta } from './accessState'
import { useAccessActions } from './useAccessActions'

const store = usePortalAdminStore()
const actions = useAccessActions()
onMounted(() => { void store.loadInvitations() })
</script>

<style scoped>
.rows { list-style: none; margin: 0; padding: 0; border: 1px solid var(--jf-color-border); border-radius: var(--jf-radius-lg); background: var(--jf-color-card); }
.row { display: flex; flex-wrap: wrap; gap: var(--jf-space-1) var(--jf-space-2); align-items: center; padding: var(--jf-space-1-5) var(--jf-space-2); border-bottom: 1px solid var(--jf-color-border); }
.row:last-child { border-bottom: 0; }
.row__main { flex: 1 1 16rem; display: flex; flex-direction: column; min-width: 0; }
.meta { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); overflow-wrap: anywhere; }
.row__actions { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); }
.row__actions :deep(.p-button) { min-height: var(--jf-touch-target); }
</style>
