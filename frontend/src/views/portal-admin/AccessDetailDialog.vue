<template>
  <Dialog :visible="visible" modal :header="store.detail?.name ?? 'Portalzugang'" :style="{ width: '40rem', maxWidth: '96vw' }" @update:visible="$emit('update:visible', $event)">
    <StateView v-if="store.detailLoading" kind="loading" />
    <StateView v-else-if="store.detailError" kind="error" :message="store.detailError" @retry="$emit('reload')" />
    <div v-else-if="store.detail" class="detail">
      <p class="detail__head">
        <StatusBadge :label="accessStateMeta[store.detail.state].label" :severity="accessStateMeta[store.detail.state].severity" :icon="accessStateMeta[store.detail.state].icon" />
        <ContactLink v-if="store.detail.email" kind="email" :value="store.detail.email" />
        <span v-else class="muted"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> keine E-Mail hinterlegt</span>
      </p>

      <section aria-labelledby="pa-account">
        <h3 id="pa-account">Konto</h3>
        <dl v-if="store.detail.account" class="facts">
          <dt>Benutzername</dt><dd>{{ store.detail.account.username }}</dd>
          <dt>Letzte Anmeldung</dt><dd>{{ store.detail.account.last_login ? formatDate(store.detail.account.last_login, true) : 'noch nie angemeldet' }}</dd>
          <dt>Verknüpft seit</dt><dd>{{ formatDate(store.detail.account.linked_at) }}</dd>
        </dl>
        <p v-else class="muted">Es besteht noch kein Konto.</p>
      </section>

      <section v-if="store.detail.kind === 'parent'" aria-labelledby="pa-children">
        <h3 id="pa-children">Zugriff pro Kind</h3>
        <p v-if="!store.detail.children.length" class="muted">Kein Kind verknüpft.</p>
        <ul v-else class="plain">
          <li v-for="child in store.detail.children" :key="child.member">
            <strong>{{ child.name }}</strong>
            <span v-if="child.ended"><StatusBadge label="Beendet" severity="danger" icon="pi pi-ban" /> Elternzugriff endete am {{ formatDate(child.access_ends_on) }}</span>
            <span v-else-if="child.access_ends_on">
              Elternzugriff bis {{ formatDate(child.access_ends_on) }}
              <StatusBadge v-if="child.ends_soon" label="Endet bald" severity="warning" />
            </span>
            <span v-else class="muted">Elternzugriff ohne Ende (Geburtstag unbekannt)</span>
            <span v-if="child.extended_until"> · verlängert bis {{ formatDate(child.extended_until) }}</span>
          </li>
        </ul>
      </section>

      <section aria-labelledby="pa-inv">
        <h3 id="pa-inv">Einladungen</h3>
        <p v-if="!store.detail.invitations.length" class="muted">Noch keine Einladung verschickt.</p>
        <ul v-else class="plain">
          <li v-for="inv in store.detail.invitations" :key="inv.id">
            <StatusBadge :label="invitationStateMeta[inv.state].label" :severity="invitationStateMeta[inv.state].severity" :icon="invitationStateMeta[inv.state].icon" />
            <span>erstellt {{ formatDate(inv.created_at, true) }} von {{ inv.created_by_name }}</span>
            <span class="muted">gültig bis {{ formatDate(inv.expires_at) }}</span>
          </li>
        </ul>
      </section>
    </div>
    <template #footer>
      <Button label="Schließen" severity="secondary" outlined @click="$emit('update:visible', false)" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import ContactLink from '@/components/common/ContactLink.vue'
import { usePortalAdminStore } from '@/stores/portalAdmin'
import { accessStateMeta, formatDate, invitationStateMeta } from './accessState'

defineProps<{ visible: boolean }>()
defineEmits<{ 'update:visible': [value: boolean], reload: [] }>()
const store = usePortalAdminStore()
</script>

<style scoped>
.detail { display: flex; flex-direction: column; gap: var(--jf-space-2); }
.detail__head { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); align-items: center; margin: 0; }
h3 { margin: 0 0 var(--jf-space-1); font-size: var(--jf-text-sm); color: var(--jf-color-text-muted); text-transform: uppercase; letter-spacing: 0.06em; }
.facts { display: grid; grid-template-columns: max-content 1fr; gap: var(--jf-space-0-5) var(--jf-space-2); margin: 0; }
.facts dt { color: var(--jf-color-text-muted); }
.facts dd { margin: 0; overflow-wrap: anywhere; }
.plain { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--jf-space-1); }
.plain li { display: flex; flex-wrap: wrap; gap: var(--jf-space-1); align-items: center; padding: var(--jf-space-1) 0; border-bottom: 1px solid var(--jf-color-border); }
.muted { color: var(--jf-color-text-muted); }
</style>
