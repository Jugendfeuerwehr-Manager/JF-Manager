<template>
  <SettingsCategoryCard
    title="LDAP Einstellungen"
    description="LDAP Anmeldung, Gruppen-Synchronisation und Abteilungsrollen konfigurieren"
    icon="pi pi-shield"
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
        <template #header><span class="font-semibold">Wie funktioniert LDAP in JF-Manager?</span></template>
        <div class="text-sm line-height-3">
          <p class="mb-2"><strong>Authentifizierung:</strong> Wenn LDAP aktiviert ist, versucht JF-Manager zuerst den Login über den konfigurierten LDAP-Server. Schlägt das fehl, kann der Benutzer sein lokales Passwort verwenden (Fallback).</p>
          <p class="mb-2"><strong>Server URI:</strong> Adresse des LDAP-Servers, z. B. <code>ldap://ldap.example.org</code> oder <code>ldaps://ldap.example.org:636</code>. LDAPS verschlüsselt direkt; STARTTLS startet unverschlüsselt und wechselt dann zu TLS.</p>
          <p class="mb-2"><strong>Bind DN / Passwort:</strong> Zugangsdaten eines Dienstkontos für Verzeichnissuche. Leer lassen für anonymen Bind.</p>
          <p class="mb-2"><strong>User Base DN:</strong> LDAP-Pfad unter dem Benutzer gesucht werden, z. B. <code>ou=users,dc=example,dc=org</code>. Nutze den <em>Durchsuchen</em>-Button um den Baum zu erkunden.</p>
          <p class="mb-2"><strong>User Search Filter:</strong> LDAP-Filter zur Benutzersuche. <code>%(user)s</code> wird durch den eingegebenen Benutzernamen ersetzt, z. B. <code>(uid=%(user)s)</code> oder <code>(sAMAccountName=%(user)s)</code> für Active Directory.</p>
          <p class="mb-2"><strong>Group Base DN / Group Filter:</strong> Voraussetzung für Gruppen-Spiegelung und Abteilungsrollen-Mapping.</p>
          <p class="mb-2"><strong>Gruppen spiegeln:</strong> LDAP-Gruppen werden bei jedem Login als Django-Gruppen synchronisiert und dem Benutzer zugewiesen.</p>
          <p class="mb-2"><strong>Require Group:</strong> Nur Mitglieder dieser LDAP-Gruppe dürfen sich anmelden. Leer lassen für alle LDAP-Benutzer.</p>
          <p class="mb-0"><strong>Abteilungsrollen-Mapping:</strong> LDAP-Gruppen können direkt auf JF-Manager Abteilungen und Berechtigungsgruppen abgebildet werden. Bei jedem Login werden Abteilungszugehörigkeiten automatisch aktualisiert. Mit <em>Aufheben bei Nichtübereinstimmung</em> werden Rollen auch entzogen wenn der Benutzer die LDAP-Gruppe verlässt.</p>
        </div>
      </Panel>
    </div>

    <form @submit.prevent="handleSubmit">
      <SettingsCheckbox
        v-model="formData.enabled"
        label="LDAP Anmeldung aktivieren"
        field-id="ldap_enabled"
        help-text="Wenn aktiviert, wird LDAP vor lokaler Anmeldung geprüft"
        :disabled="!canEdit"
      />

      <div class="grid">
        <div class="col-12 md:col-8">
          <SettingsTextField
            v-model="formData.server_uri"
            label="LDAP Server URI"
            field-id="ldap_server_uri"
            placeholder="ldap://ldap.example.org"
            :disabled="!canEdit"
          />
        </div>
        <div class="col-12 md:col-4 flex align-items-center">
          <SettingsCheckbox
            v-model="formData.start_tls"
            label="STARTTLS"
            field-id="ldap_start_tls"
            :disabled="!canEdit"
          />
        </div>
      </div>

      <SettingsCheckbox
        v-model="formData.disable_cert_validation"
        label="TLS Zertifikatsprüfung deaktivieren (unsicher)"
        field-id="ldap_disable_cert_validation"
        help-text="Nur für Testumgebungen empfohlen. In Produktion sollte die Zertifikatsprüfung aktiv bleiben."
        :disabled="!canEdit"
      />

      <SettingsTextField
        v-model="formData.ca_cert_file"
        label="CA Zertifikat Datei (optional)"
        field-id="ldap_ca_cert_file"
        placeholder="/etc/ssl/certs/internal-ldap-ca.pem"
        :disabled="!canEdit || formData.disable_cert_validation"
      />

      <div class="field">
        <label for="ldap_ca_cert_content" class="block mb-2">CA Zertifikat Inhalt (PEM, optional)</label>
        <Textarea
          id="ldap_ca_cert_content"
          v-model="formData.ca_cert_content"
          class="w-full"
          rows="6"
          autoResize
          placeholder="-----BEGIN CERTIFICATE-----"
          :disabled="!canEdit || formData.disable_cert_validation"
        />
        <small class="text-color-secondary">
          Verwende entweder Dateipfad oder PEM-Inhalt. Ohne Angabe wird der System-Truststore genutzt.
        </small>
      </div>

      <div class="grid">
        <div class="col-12 md:col-6">
          <SettingsTextField
            v-model="formData.bind_dn"
            label="Bind DN"
            field-id="ldap_bind_dn"
            placeholder="cn=admin,dc=example,dc=org"
            :disabled="!canEdit"
          />
        </div>
        <div class="col-12 md:col-6">
          <div class="field">
            <label for="ldap_bind_password" class="block mb-2">Bind Passwort</label>
            <Password
              id="ldap_bind_password"
              v-model="formData.bind_password"
              toggleMask
              :feedback="false"
              class="w-full"
              inputClass="w-full"
              :disabled="!canEdit"
              placeholder="********"
            />
            <small class="text-color-secondary">{{
              formData.has_bind_password
                ? 'Passwort gespeichert. Nur bei Änderung neu setzen.'
                : 'Kein Passwort gespeichert.'
            }}</small>
          </div>
        </div>
      </div>

      <!-- User Base DN with browse -->
      <div class="field">
        <label for="ldap_user_search_base_dn" class="block mb-2">User Base DN</label>
        <div class="flex gap-2">
          <InputText
            id="ldap_user_search_base_dn"
            v-model="formData.user_search_base_dn"
            placeholder="ou=users,dc=example,dc=org"
            class="flex-1"
            :disabled="!canEdit"
          />
          <Button
            icon="pi pi-sitemap"
            label="Durchsuchen"
            severity="secondary"
            outlined
            :disabled="!canEdit || !formData.server_uri"
            @click.prevent="openBrowseDialog('user_search_base_dn')"
          />
        </div>
      </div>

      <SettingsTextField
        v-model="formData.user_search_filter"
        label="User Search Filter"
        field-id="ldap_user_search_filter"
        placeholder="(uid=%(user)s)"
        :disabled="!canEdit"
      />

      <!-- Group Base DN with browse -->
      <div class="field">
        <label for="ldap_group_search_base_dn" class="block mb-2">Group Base DN (OU)</label>
        <div class="flex gap-2">
          <InputText
            id="ldap_group_search_base_dn"
            v-model="formData.group_search_base_dn"
            placeholder="ou=groups,dc=example,dc=org"
            class="flex-1"
            :disabled="!canEdit"
          />
          <Button
            icon="pi pi-sitemap"
            label="Durchsuchen"
            severity="secondary"
            outlined
            :disabled="!canEdit || !formData.server_uri"
            @click.prevent="openBrowseDialog('group_search_base_dn')"
          />
        </div>
      </div>

      <SettingsTextField
        v-model="formData.group_search_filter"
        label="Group Search Filter"
        field-id="ldap_group_search_filter"
        placeholder="(objectClass=groupOfNames)"
        :disabled="!canEdit"
      />

      <div class="field">
        <label for="ldap_group_type" class="block mb-2">Group Type</label>
        <Dropdown
          id="ldap_group_type"
          v-model="formData.group_type"
          :options="groupTypeOptions"
          optionLabel="label"
          optionValue="value"
          class="w-full"
          :disabled="!canEdit"
        />
      </div>

      <SettingsCheckbox
        v-model="formData.mirror_groups"
        label="LDAP Gruppen spiegeln"
        field-id="ldap_mirror_groups"
        help-text="LDAP Gruppen werden bei jedem Login in Django Gruppen synchronisiert"
        :disabled="!canEdit"
      />

      <!-- Require Group with browse -->
      <div class="field">
        <label for="ldap_require_group" class="block mb-2">Require Group DN (optional)</label>
        <div class="flex gap-2">
          <InputText
            id="ldap_require_group"
            v-model="formData.require_group"
            placeholder="cn=app-users,ou=groups,dc=example,dc=org"
            class="flex-1"
            :disabled="!canEdit"
          />
          <Button
            v-if="formData.group_search_base_dn"
            icon="pi pi-sitemap"
            label="Durchsuchen"
            severity="secondary"
            outlined
            :disabled="!canEdit || !formData.server_uri"
            @click.prevent="openBrowseDialog('require_group', formData.group_search_base_dn)"
          />
        </div>
      </div>

      <div class="flex justify-content-end gap-2 mt-4">
        <Button
          label="Verbindung testen"
          severity="info"
          outlined
          icon="pi pi-check-circle"
          @click.prevent="handleTestConnection"
          :loading="testingConn"
          :disabled="!canEdit || !formData.server_uri"
        />
        <Button label="Abbrechen" severity="secondary" @click="handleCancel" :disabled="!hasChanges" />
        <Button label="Speichern" type="submit" :loading="saving" :disabled="!canEdit || !hasChanges" />
      </div>
    </form>

    <div v-if="connTestResult" class="mt-3">
      <Message :severity="connTestResult.ok ? 'success' : 'error'" :closable="true" @close="connTestResult = null">
        {{ connTestResult.detail }}
      </Message>
    </div>

    <template v-if="successMessage || errorMessage" #footer>
      <Message v-if="successMessage" severity="success" :closable="false">{{ successMessage }}</Message>
      <Message v-if="errorMessage" severity="error" :closable="true" @close="errorMessage = ''">
        {{ errorMessage }}
      </Message>
    </template>
  </SettingsCategoryCard>

  <!-- Department Role Mappings -->
  <SettingsCategoryCard
    title="Abteilungsrollen-Mapping"
    description="LDAP-Gruppen automatisch auf JF-Manager Abteilungen und Rollen abbilden"
    icon="pi pi-users"
    class="mt-4"
  >
    <div class="mb-3 text-sm text-color-secondary">
      Bei jedem LDAP-Login werden die konfigurierten Mappings geprüft und die Abteilungszugehörigkeit des Benutzers
      aktualisiert. Voraussetzung: Group Base DN und Group Search Filter sind konfiguriert.
    </div>

    <DataTable
      :value="settingsStore.departmentMappings"
      :loading="loadingMappings"
      class="mb-3"
      emptyMessage="Keine Mappings konfiguriert."
    >
      <Column field="ldap_group_dn" header="LDAP Group DN" style="min-width: 14rem">
        <template #body="{ data }"><code class="text-sm">{{ data.ldap_group_dn }}</code></template>
      </Column>
      <Column field="department_name" header="Abteilung" style="min-width: 10rem" />
      <Column field="auth_groups" header="Berechtigungsgruppen" style="min-width: 10rem">
        <template #body="{ data }">
          <Tag v-for="g in data.auth_groups" :key="g.id" :value="g.name" class="mr-1" severity="secondary" />
          <span v-if="!data.auth_groups.length" class="text-color-secondary text-sm">–</span>
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
            @click="confirmDeleteMapping(data)"
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

  <!-- Browse LDAP dialog -->
  <Dialog
    v-model:visible="browseDialogVisible"
    header="LDAP durchsuchen"
    :modal="true"
    :style="{ width: '60rem', maxWidth: '95vw' }"
    :draggable="false"
  >
    <div class="mb-3">
      <label class="block mb-1 font-medium text-sm">Base DN</label>
      <div class="flex gap-2">
        <InputText v-model="browseBaseDn" class="flex-1" placeholder="dc=example,dc=org" />
        <Button label="Laden" icon="pi pi-search" @click="executeBrowse" :loading="browsing" />
      </div>
      <div class="flex gap-2 mt-2">
        <div class="flex-1">
          <label class="block mb-1 text-sm">Filter</label>
          <InputText v-model="browseFilter" class="w-full" placeholder="(objectClass=*)" />
        </div>
        <div>
          <label class="block mb-1 text-sm">Tiefe</label>
          <Dropdown
            v-model="browseScope"
            :options="[
              { label: 'Eine Ebene', value: 'one' },
              { label: 'Rekursiv', value: 'subtree' }
            ]"
            optionLabel="label"
            optionValue="value"
          />
        </div>
      </div>
    </div>

    <Message v-if="browseError" severity="error" :closable="false" class="mb-2">{{ browseError }}</Message>

    <div v-if="browseEntries.length > 0">
      <div class="text-sm text-color-secondary mb-2">
        {{ browseEntries.length }} Einträge gefunden. Klicke auf einen Eintrag um den DN zu übernehmen.
      </div>
      <DataTable
        :value="browseEntries"
        :scrollable="true"
        scrollHeight="300px"
        selectionMode="single"
        @row-click="selectBrowseEntry"
      >
        <Column field="dn" header="DN" />
        <Column header="CN / Name">
          <template #body="{ data }">{{ Array.isArray(data.cn) ? data.cn[0] : data.cn }}</template>
        </Column>
        <Column header="Typ">
          <template #body="{ data }">
            <span class="text-sm text-color-secondary">{{
              Array.isArray(data.objectClass) ? data.objectClass.join(', ') : data.objectClass
            }}</span>
          </template>
        </Column>
      </DataTable>
    </div>
    <div v-else-if="!browsing && browseSearched" class="text-color-secondary text-sm">
      Keine Einträge gefunden.
    </div>

    <template #footer>
      <Button label="Schließen" severity="secondary" @click="browseDialogVisible = false" />
    </template>
  </Dialog>

  <!-- Add mapping dialog -->
  <Dialog
    v-model:visible="addMappingDialogVisible"
    header="Abteilungsrollen-Mapping hinzufügen"
    :modal="true"
    :style="{ width: '50rem', maxWidth: '95vw' }"
    :draggable="false"
  >
    <div class="field">
      <label class="block mb-1 font-medium">LDAP Group DN</label>
      <div class="flex gap-2">
        <InputText
          v-model="newMapping.ldap_group_dn"
          class="flex-1"
          placeholder="cn=jf-admins,ou=groups,dc=example,dc=org"
        />
        <Button
          icon="pi pi-sitemap"
          label="Durchsuchen"
          severity="secondary"
          outlined
          :disabled="!formData.server_uri"
          @click="openBrowseForMapping"
        />
      </div>
    </div>

    <div class="field">
      <label class="block mb-1 font-medium">Abteilung</label>
      <Dropdown
        v-model="newMapping.department"
        :options="departments"
        optionLabel="name"
        optionValue="id"
        class="w-full"
        placeholder="Abteilung wählen..."
        :loading="loadingDepartments"
      />
    </div>

    <div class="field">
      <label class="block mb-1 font-medium">Berechtigungsgruppen (optional)</label>
      <MultiSelect
        v-model="newMapping.auth_group_ids"
        :options="authGroups"
        optionLabel="name"
        optionValue="id"
        class="w-full"
        placeholder="Django-Gruppen wählen..."
        :loading="loadingAuthGroups"
        display="chip"
      />
      <small class="text-color-secondary">Die gewählten Gruppen werden dem Benutzer in dieser Abteilung zugewiesen.</small>
    </div>

    <div class="field">
      <SettingsCheckbox
        v-model="newMapping.revoke_on_mismatch"
        label="Aufheben bei Nichtübereinstimmung"
        field-id="new_mapping_revoke"
        help-text="Abteilungszugehörigkeit entziehen wenn der Benutzer die LDAP-Gruppe verlässt"
      />
    </div>

    <Message v-if="addMappingError" severity="error" :closable="false" class="mt-2">{{ addMappingError }}</Message>

    <template #footer>
      <Button label="Abbrechen" severity="secondary" @click="addMappingDialogVisible = false" />
      <Button
        label="Hinzufügen"
        icon="pi pi-check"
        :loading="savingMapping"
        :disabled="!newMapping.ldap_group_dn || !newMapping.department"
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
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import SettingsCategoryCard from '../atoms/SettingsCategoryCard.vue'
import SettingsTextField from '../atoms/SettingsTextField.vue'
import SettingsCheckbox from '../atoms/SettingsCheckbox.vue'
import { useSettingsStore } from '@/stores/settings'
import type { LdapSettings, LdapBrowseEntry, LdapDepartmentRoleMapping } from '@/types/settings'
import apiClient from '@/api/index'

interface Props {
  settings: LdapSettings | null
  canEdit: boolean
  saving?: boolean
}

interface Emits {
  (e: 'save', data: Partial<LdapSettings>): void
}

const props = withDefaults(defineProps<Props>(), {
  saving: false,
})

const emit = defineEmits<Emits>()
const confirm = useConfirm()
const settingsStore = useSettingsStore()

const groupTypeOptions = [
  { label: 'GroupOfNames (POSIX / OpenLDAP)', value: 'group_of_names' },
  { label: 'Active Directory', value: 'active_directory' },
]

const helpExpanded = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const testingConn = ref(false)
const connTestResult = ref<{ ok: boolean; detail: string } | null>(null)

const formData = reactive<LdapSettings>({
  enabled: false,
  server_uri: '',
  start_tls: false,
  ca_cert_file: '',
  ca_cert_content: '',
  disable_cert_validation: false,
  bind_dn: '',
  bind_password: '',
  has_bind_password: false,
  user_search_base_dn: '',
  user_search_filter: '(uid=%(user)s)',
  group_search_base_dn: '',
  group_search_filter: '(objectClass=groupOfNames)',
  group_type: 'group_of_names',
  mirror_groups: true,
  require_group: '',
})

const originalData = ref<LdapSettings | null>(null)

watch(
  () => props.settings,
  (s) => {
    if (!s) return
    formData.enabled = s.enabled
    formData.server_uri = s.server_uri || ''
    formData.start_tls = s.start_tls ?? false
    formData.ca_cert_file = s.ca_cert_file || ''
    formData.ca_cert_content = s.ca_cert_content || ''
    formData.disable_cert_validation = s.disable_cert_validation ?? false
    formData.bind_dn = s.bind_dn || ''
    formData.bind_password = ''
    formData.has_bind_password = s.has_bind_password ?? false
    formData.user_search_base_dn = s.user_search_base_dn || ''
    formData.user_search_filter = s.user_search_filter || '(uid=%(user)s)'
    formData.group_search_base_dn = s.group_search_base_dn || ''
    formData.group_search_filter = s.group_search_filter || '(objectClass=groupOfNames)'
    formData.group_type = s.group_type || 'group_of_names'
    formData.mirror_groups = s.mirror_groups ?? true
    formData.require_group = s.require_group || ''
    originalData.value = { ...s, bind_password: '' }
  },
  { immediate: true },
)

const hasChanges = computed(() => {
  const o = originalData.value
  if (!o) return false
  return (
    formData.enabled !== o.enabled ||
    formData.server_uri !== o.server_uri ||
    formData.start_tls !== o.start_tls ||
    formData.ca_cert_file !== o.ca_cert_file ||
    formData.ca_cert_content !== o.ca_cert_content ||
    formData.disable_cert_validation !== o.disable_cert_validation ||
    formData.bind_dn !== o.bind_dn ||
    formData.user_search_base_dn !== o.user_search_base_dn ||
    formData.user_search_filter !== o.user_search_filter ||
    formData.group_search_base_dn !== o.group_search_base_dn ||
    formData.group_search_filter !== o.group_search_filter ||
    formData.group_type !== o.group_type ||
    formData.mirror_groups !== o.mirror_groups ||
    formData.require_group !== o.require_group ||
    !!formData.bind_password
  )
})

function handleSubmit() {
  if (formData.enabled) {
    const missing: string[] = []
    if (!formData.server_uri) missing.push('LDAP Server URI')
    if (!formData.user_search_base_dn) missing.push('User Base DN')
    if (!formData.user_search_filter) missing.push('User Search Filter')
    if (missing.length > 0) {
      errorMessage.value = `Bitte ausfüllen: ${missing.join(', ')}`
      return
    }
  }

  if (formData.ca_cert_file && formData.ca_cert_content) {
    errorMessage.value = 'Bitte entweder CA Zertifikat Datei oder CA Zertifikat Inhalt verwenden.'
    return
  }

  const o = originalData.value
  const payload: Partial<LdapSettings> = {}
  if (formData.enabled !== o?.enabled) payload.enabled = formData.enabled
  if (formData.server_uri !== o?.server_uri) payload.server_uri = formData.server_uri
  if (formData.start_tls !== o?.start_tls) payload.start_tls = formData.start_tls
  if (formData.ca_cert_file !== o?.ca_cert_file) payload.ca_cert_file = formData.ca_cert_file
  if (formData.ca_cert_content !== o?.ca_cert_content) payload.ca_cert_content = formData.ca_cert_content
  if (formData.disable_cert_validation !== o?.disable_cert_validation) {
    payload.disable_cert_validation = formData.disable_cert_validation
  }
  if (formData.bind_dn !== o?.bind_dn) payload.bind_dn = formData.bind_dn
  if (formData.user_search_base_dn !== o?.user_search_base_dn)
    payload.user_search_base_dn = formData.user_search_base_dn
  if (formData.user_search_filter !== o?.user_search_filter)
    payload.user_search_filter = formData.user_search_filter
  if (formData.group_search_base_dn !== o?.group_search_base_dn)
    payload.group_search_base_dn = formData.group_search_base_dn
  if (formData.group_search_filter !== o?.group_search_filter)
    payload.group_search_filter = formData.group_search_filter
  if (formData.group_type !== o?.group_type) payload.group_type = formData.group_type
  if (formData.mirror_groups !== o?.mirror_groups) payload.mirror_groups = formData.mirror_groups
  if (formData.require_group !== o?.require_group) payload.require_group = formData.require_group
  if (formData.bind_password) payload.bind_password = formData.bind_password
  if (Object.keys(payload).length === 0) return
  emit('save', payload)
  successMessage.value = 'LDAP Einstellungen gespeichert'
  setTimeout(() => {
    successMessage.value = ''
  }, 3000)
}

function handleCancel() {
  const o = originalData.value
  if (!o) return
  formData.enabled = o.enabled
  formData.server_uri = o.server_uri
  formData.start_tls = o.start_tls
  formData.ca_cert_file = o.ca_cert_file
  formData.ca_cert_content = o.ca_cert_content
  formData.disable_cert_validation = o.disable_cert_validation
  formData.bind_dn = o.bind_dn
  formData.bind_password = ''
  formData.has_bind_password = o.has_bind_password
  formData.user_search_base_dn = o.user_search_base_dn
  formData.user_search_filter = o.user_search_filter
  formData.group_search_base_dn = o.group_search_base_dn
  formData.group_search_filter = o.group_search_filter
  formData.group_type = o.group_type
  formData.mirror_groups = o.mirror_groups
  formData.require_group = o.require_group
  errorMessage.value = ''
}

async function handleTestConnection() {
  testingConn.value = true
  connTestResult.value = null
  try {
    const result = await settingsStore.testLdapConnection()
    connTestResult.value = result
  } catch {
    connTestResult.value = { ok: false, detail: 'Verbindungstest fehlgeschlagen.' }
  } finally {
    testingConn.value = false
  }
}

// Browse dialog
type BrowseTargetField =
  | 'user_search_base_dn'
  | 'group_search_base_dn'
  | 'require_group'
  | 'mapping_group_dn'
  | null

const browseDialogVisible = ref(false)
const browseTargetField = ref<BrowseTargetField>(null)
const browseBaseDn = ref('')
const browseFilter = ref('(objectClass=*)')
const browseScope = ref<'one' | 'subtree'>('one')
const browsing = ref(false)
const browseError = ref('')
const browseEntries = ref<LdapBrowseEntry[]>([])
const browseSearched = ref(false)

function openBrowseDialog(field: BrowseTargetField, initialDn?: string) {
  browseTargetField.value = field
  browseBaseDn.value =
    initialDn ??
    (field === 'user_search_base_dn' ? formData.user_search_base_dn : formData.group_search_base_dn) ??
    ''
  browseFilter.value = '(objectClass=*)'
  browseScope.value = 'one'
  browseEntries.value = []
  browseError.value = ''
  browseSearched.value = false
  browseDialogVisible.value = true
}

async function executeBrowse() {
  if (!browseBaseDn.value) return
  browsing.value = true
  browseError.value = ''
  browseSearched.value = false
  try {
    const result = await settingsStore.browseLdapDn({
      base_dn: browseBaseDn.value,
      filter: browseFilter.value || '(objectClass=*)',
      scope: browseScope.value,
    })
    if (!result.ok) {
      browseError.value = result.detail ?? 'Fehler beim Durchsuchen des LDAP-Verzeichnisses.'
      browseEntries.value = []
    } else {
      browseEntries.value = result.entries
    }
    browseSearched.value = true
  } catch {
    browseError.value = 'Verbindungsfehler beim Durchsuchen.'
    browseEntries.value = []
  } finally {
    browsing.value = false
  }
}

function selectBrowseEntry(event: { data: LdapBrowseEntry }) {
  const dn = event.data.dn
  if (browseTargetField.value === 'user_search_base_dn') {
    formData.user_search_base_dn = dn
    browseDialogVisible.value = false
  } else if (browseTargetField.value === 'group_search_base_dn') {
    formData.group_search_base_dn = dn
    browseDialogVisible.value = false
  } else if (browseTargetField.value === 'require_group') {
    formData.require_group = dn
    browseDialogVisible.value = false
  } else if (browseTargetField.value === 'mapping_group_dn') {
    newMapping.ldap_group_dn = dn
    browseDialogVisible.value = false
    addMappingDialogVisible.value = true
  }
}

// Department mappings
const loadingMappings = ref(false)

interface Department {
  id: number
  name: string
}
interface AuthGroup {
  id: number
  name: string
}

const departments = ref<Department[]>([])
const authGroups = ref<AuthGroup[]>([])
const loadingDepartments = ref(false)
const loadingAuthGroups = ref(false)

const addMappingDialogVisible = ref(false)
const savingMapping = ref(false)
const addMappingError = ref('')
const newMapping = reactive({
  ldap_group_dn: '',
  department: null as number | null,
  auth_group_ids: [] as number[],
  revoke_on_mismatch: false,
})

onMounted(async () => {
  loadingMappings.value = true
  try {
    await settingsStore.fetchDepartmentMappings()
  } finally {
    loadingMappings.value = false
  }
})

async function openAddMappingDialog() {
  newMapping.ldap_group_dn = ''
  newMapping.department = null
  newMapping.auth_group_ids = []
  newMapping.revoke_on_mismatch = false
  addMappingError.value = ''

  if (departments.value.length === 0) {
    loadingDepartments.value = true
    try {
      const resp = await apiClient.get('/departments/')
      const data = resp.data
      if (Array.isArray(data)) {
        departments.value = data as Department[]
      } else if (data && typeof data === 'object' && 'results' in data) {
        departments.value = (data as { results: Department[] }).results
      }
    } finally {
      loadingDepartments.value = false
    }
  }

  if (authGroups.value.length === 0) {
    loadingAuthGroups.value = true
    try {
      const resp = await apiClient.get('/admin/groups/')
      const data = resp.data
      if (Array.isArray(data)) {
        authGroups.value = data as AuthGroup[]
      } else if (data && typeof data === 'object' && 'results' in data) {
        authGroups.value = (data as { results: AuthGroup[] }).results
      }
    } finally {
      loadingAuthGroups.value = false
    }
  }

  addMappingDialogVisible.value = true
}

function openBrowseForMapping() {
  addMappingDialogVisible.value = false
  browseTargetField.value = 'mapping_group_dn'
  browseBaseDn.value = formData.group_search_base_dn || ''
  browseFilter.value = formData.group_search_filter || '(objectClass=*)'
  browseScope.value = 'subtree'
  browseEntries.value = []
  browseError.value = ''
  browseSearched.value = false
  browseDialogVisible.value = true
}

async function submitNewMapping() {
  if (!newMapping.ldap_group_dn || !newMapping.department) return
  savingMapping.value = true
  addMappingError.value = ''
  try {
    await settingsStore.createDepartmentMapping({
      ldap_group_dn: newMapping.ldap_group_dn,
      department: newMapping.department,
      auth_group_ids: newMapping.auth_group_ids,
      revoke_on_mismatch: newMapping.revoke_on_mismatch,
    })
    addMappingDialogVisible.value = false
  } catch (err: unknown) {
    addMappingError.value = err instanceof Error ? err.message : 'Fehler beim Speichern.'
  } finally {
    savingMapping.value = false
  }
}

function confirmDeleteMapping(mapping: LdapDepartmentRoleMapping) {
  confirm.require({
    message: `Mapping für "${mapping.ldap_group_dn}" wirklich löschen?`,
    header: 'Mapping löschen',
    icon: 'pi pi-exclamation-triangle',
    rejectLabel: 'Abbrechen',
    acceptLabel: 'Löschen',
    accept: () => settingsStore.deleteDepartmentMapping(mapping.id),
  })
}
</script>
