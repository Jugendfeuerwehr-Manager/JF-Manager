<template>
  <SettingsCategoryCard
    title="OIDC / SSO Einstellungen"
    description="Single Sign-On via OpenID Connect konfigurieren (z. B. Nextcloud, Keycloak)"
    icon="pi pi-sign-in"
  >
    <!-- Help section -->
    <div class="mb-4">
      <Button
        :label="helpExpanded ? 'Hilfe ausblenden' : 'Hilfe & Erklärung anzeigen'"
        icon="pi pi-question-circle"
        severity="secondary"
        text
        @click="helpExpanded = !helpExpanded"
      />
      <Panel v-if="helpExpanded" class="mt-2">
        <template #header><span class="font-semibold">Einrichtung & Konfiguration</span></template>
        <div class="text-sm line-height-3">

          <p class="font-semibold mb-1 mt-0">Anmeldeprozess</p>
          <p class="mb-3">Benutzer klickt auf "Mit SSO anmelden" → wird zum Identity Provider weitergeleitet → kehrt nach erfolgreichem Login zurück. JF-Manager nutzt den <strong>Authorization Code Flow</strong> (PKCE-kompatibel).</p>

          <p class="font-semibold mb-1">Nextcloud als OIDC-Provider einrichten</p>
          <ol class="mb-3 pl-3">
            <li class="mb-1">Nextcloud-App <strong>"OIDC Identity Provider"</strong> installieren (Einstellungen → Apps).</li>
            <li class="mb-1">Unter <em>Einstellungen → Sicherheit → OAuth 2.0-Clients</em> einen neuen Client anlegen.</li>
            <li class="mb-1"><strong>Redirect URI:</strong> <code>{{ redirectUri }}</code></li>
            <li class="mb-1"><strong>Flow:</strong> Authorization Code. Implicit Flow <em>nicht</em> aktivieren.</li>
            <li class="mb-1"><strong>Token-Typ:</strong> ID-Token (JWT). Access Token wird von JF-Manager nicht gespeichert.</li>
            <li class="mb-1"><strong>Signing-Algorithmus:</strong> RS256 (Standard). JF-Manager erwartet RS256-signierte Tokens.</li>
            <li class="mb-1">Client ID und Client Secret aus Nextcloud hier eintragen.</li>
            <li class="mb-1"><strong>Issuer URL</strong> ist die Basis-URL deiner Nextcloud, z. B. <code>https://cloud.example.org</code>. Die Discovery wird automatisch unter <code>/.well-known/openid-configuration</code> geladen.</li>
          </ol>

          <p class="font-semibold mb-1">Gruppen in Nextcloud übertragen</p>
          <p class="mb-1">Damit Gruppen im Token erscheinen, muss in Nextcloud der <strong>groups-Claim</strong> aktiviert sein:</p>
          <ul class="mb-3 pl-3">
            <li class="mb-1">Nextcloud-App <strong>"User OIDC"</strong> oder "OIDC Identity Provider" → Claim-Einstellungen → <em>groups</em> aktivieren.</li>
            <li class="mb-1">Der Claim-Name lautet standardmäßig <code>groups</code>. Diesen Wert hier unter <em>Groups Claim</em> eintragen.</li>
            <li class="mb-1">Erforderliche Scopes: <code>openid email profile</code> (groups wird meist automatisch hinzugefügt).</li>
          </ul>

          <p class="font-semibold mb-1">Wie funktioniert das Gruppen-Mapping?</p>
          <p class="mb-1">Der <strong>groups</strong>-Claim enthält eine Liste der Nextcloud-Gruppen des Benutzers (z. B. <code>["JF-Wache1", "JF-Admin"]</code>). Pro Eintrag im Gruppen-Mapping wird geprüft, ob der Benutzer Mitglied der angegebenen Nextcloud-Gruppe ist. Bei Übereinstimmung werden ihm automatisch zugewiesen:</p>
          <ul class="mb-3 pl-3">
            <li class="mb-1"><strong>Abteilung (Wache):</strong> Die JF-Manager-Abteilung, der der Benutzer angehören soll. Dies sind die Wachen/Gruppen innerhalb von JF-Manager, <em>nicht</em> Nextcloud-Gruppen.</li>
            <li class="mb-1"><strong>Berechtigungsgruppen:</strong> Django-Berechtigungsgruppen (z. B. "Gruppenführer", "Kassierer"), die bestimmen welche Funktionen der Benutzer in dieser Abteilung nutzen darf. Diese sind ebenfalls in JF-Manager definiert, <em>nicht</em> in Nextcloud.</li>
          </ul>
          <p class="mb-3">Beispiel: Nextcloud-Gruppe <code>JF-Wache1</code> → Abteilung "Wache 1" + Berechtigungsgruppe "Mitglied". Nextcloud-Gruppe <code>JF-Admin</code> → Abteilung "Alle" + Berechtigungsgruppe "Administrator".</p>

          <p class="font-semibold mb-1">Staff- und Admin-Gruppen</p>
          <p class="mb-0">Benutzer in der <em>Staff-Gruppe</em> erhalten Django-Staff-Rechte (Zugang zum Admin-Backend). Benutzer in der <em>Admin-Gruppe</em> erhalten Superuser-Rechte. Diese Gruppen sind Nextcloud-Gruppen-Namen.</p>
        </div>
      </Panel>
    </div>

    <form @submit.prevent="handleSubmit">
      <SettingsCheckbox
        v-model="formData.enabled"
        label="OIDC / SSO aktivieren"
        field-id="oidc_enabled"
        help-text="Wenn aktiviert, erscheint ein SSO-Button auf der Login-Seite"
        :disabled="!canEdit"
      />

      <SettingsTextField
        v-model="formData.provider_name"
        label="Provider Name"
        field-id="oidc_provider_name"
        placeholder="SSO"
        help-text='Anzeigename auf dem Login-Button, z. B. "Nextcloud" oder "Keycloak"'
        :disabled="!canEdit"
      />

      <div class="grid">
        <div class="col-12 md:col-9">
          <SettingsTextField
            v-model="formData.issuer_url"
            label="Issuer URL"
            field-id="oidc_issuer_url"
            placeholder="https://nextcloud.example.org"
            :disabled="!canEdit"
          />
        </div>
        <div class="col-12 md:col-3 flex align-items-end pb-2">
          <Button
            label="Testen"
            icon="pi pi-search"
            severity="info"
            outlined
            :loading="testingDiscovery"
            :disabled="!formData.issuer_url"
            @click.prevent="handleTestDiscovery"
          />
        </div>
      </div>

      <div v-if="discoveryResult" class="mb-3">
        <Message :severity="discoveryResult.ok ? 'success' : 'error'" :closable="true" @close="discoveryResult = null">
          <template v-if="discoveryResult.ok">
            Discovery erfolgreich. Issuer: <code>{{ discoveryResult.issuer }}</code>
          </template>
          <template v-else>
            {{ discoveryResult.detail || 'Discovery fehlgeschlagen.' }}
          </template>
        </Message>
        <div v-if="discoveryResult.ok" class="mt-2 text-sm text-color-secondary">
          <div v-if="discoveryResult.authorization_endpoint">Authorization: {{ discoveryResult.authorization_endpoint }}</div>
          <div v-if="discoveryResult.token_endpoint">Token: {{ discoveryResult.token_endpoint }}</div>
          <div v-if="discoveryResult.userinfo_endpoint">UserInfo: {{ discoveryResult.userinfo_endpoint }}</div>
          <div v-if="discoveryResult.scopes_supported?.length">
            Scopes: {{ discoveryResult.scopes_supported.join(', ') }}
          </div>
        </div>
      </div>

      <SettingsTextField
        v-model="formData.client_id"
        label="Client ID"
        field-id="oidc_client_id"
        placeholder="jf-manager"
        :disabled="!canEdit"
      />

      <div class="field">
        <label for="oidc_client_secret" class="block mb-2">
          Client Secret
          <Tag v-if="formData.has_client_secret" value="gespeichert" severity="success" class="ml-2" />
        </label>
        <Password
          id="oidc_client_secret"
          v-model="formData.client_secret"
          toggleMask
          :feedback="false"
          class="w-full"
          inputClass="w-full"
          :disabled="!canEdit"
          :placeholder="formData.has_client_secret ? '(unverändert lassen wenn kein neues Secret)' : 'Client Secret eingeben'"
        />
      </div>

      <SettingsTextField
        v-model="formData.scope"
        label="Scopes"
        field-id="oidc_scope"
        placeholder="openid email profile"
        help-text="Leerzeichen-getrennte OIDC Scopes"
        :disabled="!canEdit"
      />

      <SettingsTextField
        v-model="formData.groups_claim"
        label="Groups Claim"
        field-id="oidc_groups_claim"
        placeholder="groups"
        help-text="Name des Claims im ID-Token der die Gruppen-Liste enthält"
        :disabled="!canEdit"
      />

      <div class="grid">
        <div class="col-12 md:col-6">
          <SettingsTextField
            v-model="formData.staff_group"
            label="Staff-Gruppe"
            field-id="oidc_staff_group"
            placeholder=""
            help-text="Benutzer in dieser Gruppe erhalten Staff-Rechte"
            :disabled="!canEdit"
          />
        </div>
        <div class="col-12 md:col-6">
          <SettingsTextField
            v-model="formData.admin_group"
            label="Admin-Gruppe"
            field-id="oidc_admin_group"
            placeholder=""
            help-text="Benutzer in dieser Gruppe erhalten Superuser-Rechte"
            :disabled="!canEdit"
          />
        </div>
      </div>

      <SettingsCheckbox
        v-model="formData.require_group_mapping"
        label="Gruppen-Mapping voraussetzen"
        field-id="oidc_require_group_mapping"
        help-text="Login nur erlaubt wenn mindestens ein Abteilungsrollen-Mapping greift"
        :disabled="!canEdit"
      />

      <SettingsCheckbox
        v-model="formData.hide_local_login"
        label="Lokalen Login ausblenden"
        field-id="oidc_hide_local_login"
        help-text="Benutzername/Passwort-Formular standardmäßig auf der Login-Seite verstecken"
        :disabled="!canEdit"
      />

      <div class="flex justify-content-end gap-2 mt-3">
        <Button label="Abbrechen" severity="secondary" @click="handleCancel" :disabled="!hasChanges" />
        <Button label="Speichern" type="submit" :loading="saving" :disabled="!canEdit || !hasChanges" />
      </div>
    </form>

    <template v-if="successMessage || errorMessage" #footer>
      <Message v-if="successMessage" severity="success" :closable="false">{{ successMessage }}</Message>
      <Message v-if="errorMessage" severity="error" :closable="true" @close="errorMessage = ''">
        {{ errorMessage }}
      </Message>
    </template>
  </SettingsCategoryCard>

  <!-- Group Mappings -->
  <SettingsCategoryCard
    title="Gruppen-Mapping"
    description="OIDC Gruppen automatisch auf JF-Manager Abteilungen und Rollen abbilden"
    icon="pi pi-users"
    class="mt-4"
  >
    <div class="mb-3 text-sm text-color-secondary">
      Bei jedem OIDC-Login werden die konfigurierten Mappings geprüft und die Abteilungszugehörigkeit des Benutzers aktualisiert.
    </div>

    <DataTable
      :value="groupMappings"
      :loading="loadingMappings"
      class="mb-3"
      emptyMessage="Keine Mappings konfiguriert."
    >
      <Column field="group_claim_value" header="OIDC Gruppen-Wert" style="min-width: 12rem">
        <template #body="{ data }"><code class="text-sm">{{ data.group_claim_value }}</code></template>
      </Column>
      <Column field="department_name" header="Abteilung" style="min-width: 10rem">
        <template #body="{ data }">{{ data.department_name || '–' }}</template>
      </Column>
      <Column field="auth_groups" header="Berechtigungsgruppen" style="min-width: 10rem">
        <template #body="{ data }">
          <Tag v-for="g in data.auth_groups" :key="g.id" :value="g.name" class="mr-1" severity="secondary" />
          <span v-if="!data.auth_groups?.length" class="text-color-secondary text-sm">–</span>
        </template>
      </Column>
      <Column field="revoke_on_mismatch" header="Aufheben" style="width: 7rem">
        <template #body="{ data }">
          <i :class="data.revoke_on_mismatch ? 'pi pi-check text-green-500' : 'pi pi-times text-color-secondary'" />
        </template>
      </Column>
      <Column header="" style="width: 4rem">
        <template #body="{ data }">
          <Button
            icon="pi pi-trash"
            severity="danger"
            text
            rounded
            :disabled="!canEdit"
            @click.stop="confirmDeleteGroupMapping(data)"
          />
        </template>
      </Column>
    </DataTable>

    <Button
      v-if="canEdit"
      label="Mapping hinzufügen"
      icon="pi pi-plus"
      severity="secondary"
      outlined
      @click="openAddMappingDialog"
    />
  </SettingsCategoryCard>

  <!-- Add group mapping dialog -->
  <Dialog
    v-model:visible="addMappingDialogVisible"
    header="Gruppen-Mapping hinzufügen"
    :modal="true"
    :style="{ width: '50rem', maxWidth: '95vw' }"
    :draggable="false"
  >
    <!-- Explanation -->
    <div class="mb-3 p-3 surface-100 border-round text-sm line-height-3">
      <p class="mt-0 mb-1"><strong>Was wird hier konfiguriert?</strong></p>
      <p class="mb-1">Jedes Mapping verknüpft eine <strong>Nextcloud-Gruppe</strong> mit einer JF-Manager-Abteilung und/oder einer Berechtigungsgruppe.</p>
      <p class="mb-1">Beispiel: Nextcloud-Gruppe <code>JF-Wache1</code> → Abteilung <em>Wache 1</em> + Rolle <em>Mitglied</em></p>
      <p class="mb-0">Bei jedem Login wird geprüft, ob der Benutzer Mitglied der angegebenen Nextcloud-Gruppe ist. Falls ja, wird die Abteilungszugehörigkeit und die Berechtigungsgruppe automatisch gesetzt.</p>
    </div>

    <div class="field">
      <label class="block mb-1 font-medium">Nextcloud-Gruppe (exakter Name)</label>
      <InputText
        v-model="newMapping.group_claim_value"
        class="w-full"
        :placeholder="`z. B. JF-Wache1 (exakter Gruppenname in Nextcloud)`"
      />
      <small class="text-color-secondary">Der Wert muss exakt dem Gruppennamen im <code>{{ formData.groups_claim || 'groups' }}</code>-Claim entsprechen (Groß-/Kleinschreibung beachten).</small>
    </div>

    <div class="field">
      <label class="block mb-1 font-medium">Abteilung in JF-Manager (optional)</label>
      <Dropdown
        v-model="newMapping.department"
        :options="departments"
        optionLabel="name"
        optionValue="id"
        class="w-full"
        placeholder="Keine Abteilung zuweisen"
        showClear
        :loading="loadingDepartments"
      />
      <small class="text-color-secondary">Die JF-Manager-Wache/Abteilung, der der Benutzer zugeordnet wird. Dies sind die in JF-Manager definierten Abteilungen, nicht Nextcloud-Gruppen.</small>
    </div>

    <div class="field">
      <label class="block mb-1 font-medium">Berechtigungsgruppen in JF-Manager (optional)</label>
      <MultiSelect
        v-model="newMapping.auth_group_ids"
        :options="authGroups"
        optionLabel="name"
        optionValue="id"
        class="w-full"
        placeholder="Berechtigungsgruppen wählen..."
        :loading="loadingAuthGroups"
        display="chip"
        filter
        filterPlaceholder="Suchen..."
      />
      <small class="text-color-secondary">Bestimmt welche Funktionen der Benutzer in JF-Manager nutzen darf (z. B. "Gruppenführer", "Kassierer"). Diese Gruppen sind in JF-Manager definiert, nicht in Nextcloud.</small>
    </div>

    <div class="field">
      <SettingsCheckbox
        v-model="newMapping.revoke_on_mismatch"
        label="Aufheben bei Nichtübereinstimmung"
        field-id="new_oidc_mapping_revoke"
        help-text="Abteilungszugehörigkeit und Berechtigungen entziehen, wenn der Benutzer die Nextcloud-Gruppe verlässt"
      />
    </div>

    <Message v-if="addMappingError" severity="error" :closable="false" class="mt-2">{{ addMappingError }}</Message>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" @click="addMappingDialogVisible = false" />
      <Button
        label="Hinzufügen"
        icon="pi pi-check"
        :loading="savingMapping"
        :disabled="!newMapping.group_claim_value"
        @click="submitNewMapping"
      />
    </template>
  </Dialog>

  <ConfirmDialog />
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import MultiSelect from 'primevue/multiselect'
import Panel from 'primevue/panel'
import Password from 'primevue/password'
import Tag from 'primevue/tag'
import { useConfirm } from 'primevue/useconfirm'
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import SettingsTextField from '../atoms/SettingsTextField.vue'
import SettingsCheckbox from '../atoms/SettingsCheckbox.vue'
import { oidcApi } from '@/api/oidc'
import type { OIDCSettings, OIDCGroupMapping, OIDCDiscoveryResult } from '@/types/oidc'
import apiClient from '@/api/index'

interface Props {
  settings: OIDCSettings | null
  canEdit: boolean
  saving?: boolean
}

interface Emits {
  (e: 'save', data: Partial<OIDCSettings>): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false,
})

const emit = defineEmits<Emits>()
const confirm = useConfirm()

// Redirect URI shown in the help text — taken from backend so it's correct in
// container/reverse-proxy setups where frontend and backend have different origins.
const redirectUri = computed(
  () => props.settings?.callback_url ?? `${window.location.origin}/api/v1/auth/oidc/callback/`,
)

const helpExpanded = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const testingDiscovery = ref(false)
const discoveryResult = ref<OIDCDiscoveryResult | null>(null)

const formData = reactive<OIDCSettings>({
  enabled: false,
  provider_name: 'SSO',
  issuer_url: '',
  client_id: '',
  client_secret: '',
  has_client_secret: false,
  scope: 'openid email profile',
  groups_claim: 'groups',
  staff_group: '',
  admin_group: '',
  require_group_mapping: false,
  hide_local_login: false,
})

const originalData = ref<OIDCSettings | null>(null)

const hasChanges = computed(() => {
  if (!originalData.value) return false
  const keys = Object.keys(formData) as (keyof OIDCSettings)[]
  return keys.some((k) => formData[k] !== (originalData.value as OIDCSettings)[k])
})

watch(
  () => props.settings,
  (val) => {
    if (val) {
      Object.assign(formData, val)
      originalData.value = { ...val }
    }
  },
  { immediate: true }
)

function handleCancel() {
  if (originalData.value) {
    Object.assign(formData, originalData.value)
  }
}

async function handleSubmit() {
  successMessage.value = ''
  errorMessage.value = ''
  // Don't send client_secret if empty (means "keep existing")
  const payload: Partial<OIDCSettings> = { ...formData }
  if (!payload.client_secret) {
    delete payload.client_secret
  }
  emit('save', payload)
  successMessage.value = 'OIDC Einstellungen gespeichert.'
  originalData.value = { ...formData }
}

async function handleTestDiscovery() {
  testingDiscovery.value = true
  discoveryResult.value = null
  try {
    const response = await oidcApi.testDiscovery(formData.issuer_url)
    discoveryResult.value = response.data
  } catch {
    discoveryResult.value = { ok: false, detail: 'Verbindung fehlgeschlagen.' }
  } finally {
    testingDiscovery.value = false
  }
}

// ---------------------------------------------------------------------------
// Group mappings
// ---------------------------------------------------------------------------

const groupMappings = ref<OIDCGroupMapping[]>([])
const loadingMappings = ref(false)
const addMappingDialogVisible = ref(false)
const savingMapping = ref(false)
const addMappingError = ref('')

interface NewMapping {
  group_claim_value: string
  department: number | null
  auth_group_ids: number[]
  revoke_on_mismatch: boolean
}

const newMapping = reactive<NewMapping>({
  group_claim_value: '',
  department: null,
  auth_group_ids: [],
  revoke_on_mismatch: false,
})

const departments = ref<{ id: number; name: string }[]>([])
const loadingDepartments = ref(false)
const authGroups = ref<{ id: number; name: string }[]>([])
const loadingAuthGroups = ref(false)

onMounted(async () => {
  loadingMappings.value = true
  try {
    const mappingsResp = await oidcApi.listGroupMappings()
    groupMappings.value = mappingsResp.data
  } catch {
    // Non-fatal: table just stays empty
  } finally {
    loadingMappings.value = false
  }
})

async function openAddMappingDialog() {
  newMapping.group_claim_value = ''
  newMapping.department = null
  newMapping.auth_group_ids = []
  newMapping.revoke_on_mismatch = false
  addMappingError.value = ''

  // Lazy-load departments
  if (departments.value.length === 0) {
    loadingDepartments.value = true
    try {
      const resp = await apiClient.get('/departments/')
      const data = resp.data
      if (Array.isArray(data)) {
        departments.value = data
      } else if (data && typeof data === 'object' && 'results' in data) {
        departments.value = (data as { results: { id: number; name: string }[] }).results
      }
    } finally {
      loadingDepartments.value = false
    }
  }

  // Lazy-load Django auth groups
  if (authGroups.value.length === 0) {
    loadingAuthGroups.value = true
    try {
      const resp = await apiClient.get('/admin/groups/')
      const data = resp.data
      if (Array.isArray(data)) {
        authGroups.value = data
      } else if (data && typeof data === 'object' && 'results' in data) {
        authGroups.value = (data as { results: { id: number; name: string }[] }).results
      }
    } finally {
      loadingAuthGroups.value = false
    }
  }

  addMappingDialogVisible.value = true
}

async function submitNewMapping() {
  addMappingError.value = ''
  savingMapping.value = true
  try {
    const created = await oidcApi.createGroupMapping({
      group_claim_value: newMapping.group_claim_value,
      department: newMapping.department,
      auth_group_ids: newMapping.auth_group_ids,
      revoke_on_mismatch: newMapping.revoke_on_mismatch,
    })
    groupMappings.value.push(created.data)
    addMappingDialogVisible.value = false
    newMapping.group_claim_value = ''
    newMapping.department = null
    newMapping.auth_group_ids = []
    newMapping.revoke_on_mismatch = false
  } catch {
    addMappingError.value = 'Fehler beim Erstellen des Mappings.'
  } finally {
    savingMapping.value = false
  }
}

// Guard against double-firing the confirm dialog (can happen in DataTable row slots)
const confirmingId = ref<number | null>(null)

function confirmDeleteGroupMapping(mapping: OIDCGroupMapping) {
  if (confirmingId.value === mapping.id) return
  confirmingId.value = mapping.id
  confirm.require({
    message: `Mapping "${mapping.group_claim_value}" wirklich löschen?`,
    header: 'Löschen bestätigen',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      await oidcApi.deleteGroupMapping(mapping.id)
      groupMappings.value = groupMappings.value.filter((m) => m.id !== mapping.id)
    },
    onHide: () => {
      confirmingId.value = null
    },
  })
}
</script>
