<template>
  <Card v-if="auth.hasPerm('portal.invite_portal_account')" class="portal-card">
    <template #content>
      <div class="portal-line">
        <h2>Portalzugang</h2>
        <StateView v-if="loading" kind="loading" title="Wird geladen …" />
        <template v-else-if="error">
          <span class="muted"><i class="pi pi-exclamation-triangle" aria-hidden="true"></i> {{ error }}</span>
        </template>
        <template v-else-if="detail">
          <StatusBadge :label="accessStateMeta[detail.state].label" :severity="accessStateMeta[detail.state].severity" :icon="accessStateMeta[detail.state].icon" />
          <span v-if="!detail.email" class="muted">Ohne E-Mail ist keine Einladung möglich.</span>
          <Button v-if="primary" :label="actionLabels[primary].label" :icon="actionLabels[primary].icon" size="small" :loading="store.busy" @click="run" />
          <router-link :to="{ name: 'portal-admin' }" class="link">In der Portalverwaltung öffnen</router-link>
        </template>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import StateView from '@/components/common/StateView.vue'
import StatusBadge from '@/components/common/StatusBadge.vue'
import { portalAdminApi, type AccessDetail } from '@/api/portalAdmin'
import { useAuthStore } from '@/stores/auth'
import { usePortalAdminStore } from '@/stores/portalAdmin'
import { getApiErrorMessage } from '@/utils/apiError'
import { accessStateMeta } from './accessState'
import { actionLabels, useAccessActions, type RowAction } from './useAccessActions'

const props = defineProps<{ parentId: number }>()
const auth = useAuthStore()
const store = usePortalAdminStore()
const actions = useAccessActions()
const detail = ref<AccessDetail | null>(null)
const loading = ref(false)
const error = ref('')

const openInvitation = computed(() => detail.value?.invitations.find(i => i.state === 'open'))
const primary = computed<RowAction | null>(() => {
  const d = detail.value
  if (!d) return null
  if (d.state === 'invited' && openInvitation.value) return 'resend'
  if ((d.state === 'none' || d.state === 'expired') && d.email) return 'invite'
  return null
})

async function load() {
  loading.value = true
  error.value = ''
  try { detail.value = (await portalAdminApi.detail({ parent: props.parentId })).data } catch (err) {
    error.value = getApiErrorMessage(err, 'Portalzugang konnte nicht geladen werden.')
  } finally { loading.value = false }
}
function run() {
  if (!primary.value || !detail.value) return
  actions.request(primary.value, { kind: 'parent', id: props.parentId, name: detail.value.name, invitationId: openInvitation.value?.id }, () => { void load() })
}
onMounted(() => { if (auth.hasPerm('portal.invite_portal_account')) void load() })
</script>

<style scoped>
.portal-card { margin-bottom: var(--jf-space-2); }
.portal-line { display: flex; flex-wrap: wrap; gap: var(--jf-space-1-5); align-items: center; }
h2 { margin: 0; font-size: var(--jf-text-base); }
.muted { color: var(--jf-color-text-muted); font-size: var(--jf-text-sm); }
.link { display: inline-flex; align-items: center; min-height: var(--jf-touch-target); color: var(--jf-color-primary); }
.portal-line :deep(.p-button) { min-height: var(--jf-touch-target); }
</style>
