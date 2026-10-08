<template>
  <section class="setup-section">
    <router-link to="/settings">← Einstellungen</router-link>
    <h2>Organisation einrichten</h2>
    <p>
      Führe die fachliche Einrichtung Schritt für Schritt durch. Du kannst jederzeit zurückkehren;
      der Stand wird aus den gespeicherten Einstellungen ermittelt.
    </p>
    <p v-if="loading" role="status">Einrichtungsstand wird geladen …</p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Button v-if="error && !status" label="Erneut laden" @click="load" />
    <template v-if="status">
      <nav aria-label="Einrichtungsschritte" class="setup-steps">
        <button
          v-for="(label, index) in steps"
          :key="label"
          type="button"
          :aria-current="step === index ? 'step' : undefined"
          @click="step = index"
        >
          {{ index + 1 }}. {{ label }}
        </button>
      </nav>
      <article v-if="step === 0">
        <h3>Organisation und Erscheinungsbild</h3>
        <p>
          {{
            status.organization_configured
              ? 'Die Organisation ist benannt.'
              : 'Beginne mit Name, Kürzel, Logo und Farbschema.'
          }}
        </p>
        <router-link to="/settings/general">Name, Logo und Farbe bearbeiten →</router-link>
        <p>
          <router-link to="/settings/vocabulary"
            >Bezeichnungen wie Mitglieder, Dienstbuch und Ausbildung anpassen →</router-link
          >
        </p>
      </article>
      <article v-if="step === 1">
        <h3>Abteilungen</h3>
        <p>
          {{ status.active_departments }} aktive Abteilung(en). Abteilungen trennen fachliche
          Zugriffe innerhalb einer Organisation.
        </p>
        <p>
          Du kannst auch ohne Abteilungen arbeiten. Überspringe diesen Schritt dann; zentrale Listen
          bleiben möglich.
        </p>
        <router-link v-if="auth.hasPerm('departments.view_department')" to="/departments"
          >Abteilungen verwalten →</router-link
        >
        <p v-else>
          Für die Abteilungsverwaltung ist ein zusätzliches Verwaltungsrecht erforderlich.
        </p>
      </article>
      <article v-if="step === 2">
        <h3>Konten und erste Rollen</h3>
        <p>
          {{ status.standard_roles }} von {{ status.expected_standard_roles }} Standardrollen
          vorhanden. Sie werden bei der Installation automatisch angelegt; der Seed erhält
          bestehende Anpassungen.
        </p>
        <p>
          {{
            status.administrator_assigned
              ? 'Die Standardrolle Systemadministration ist einem aktiven Konto zugewiesen.'
              : 'Weise einem geeigneten Konto die Rolle Systemadministration zu. Der Installationszugang bleibt für die erste Einrichtung verfügbar.'
          }}
        </p>
        <p>
          Lege zuerst Konten an, wähle danach Rolle und Zuständigkeitsbereich. Prüfe die
          Wirkungsvorschau vor der Bestätigung. Neue Rollen kannst du aus einer Vorlage kopieren.
        </p>
        <div class="setup-links">
          <router-link v-if="auth.hasPerm('users.view_customuser')" to="/users"
            >Konten verwalten →</router-link
          >
          <router-link v-if="auth.hasPerm('departments.view_roletemplate')" to="/role-templates"
            >Standardrollen ansehen und kopieren →</router-link
          >
          <router-link to="/roles">Rollen mit Vorschau zuweisen →</router-link>
        </div>
      </article>
      <article v-if="step === 3">
        <h3>Standards und Stammdaten</h3>
        <p>
          Standards werden für neue Datensätze verwendet. Bestehende Dienste und Übungen ändern sich
          dadurch nicht.
        </p>
        <div class="setup-links">
          <router-link v-for="link in permittedMasterLinks" :key="link.to" :to="link.to"
            >{{ link.label }} →</router-link
          >
        </div>
      </article>
      <article v-if="step === 4">
        <h3>Optionale Integrationen und Sicherheit</h3>
        <p>
          Die lokale Anmeldung funktioniert ohne LDAP oder Single Sign-On. Verbindungstests ändern
          keine Fachdaten; eine Test-E-Mail wird nur auf ausdrücklichen Auftrag gesendet.
        </p>
        <div class="setup-links">
          <router-link v-for="link in integrationLinks" :key="link.to" :to="link.to"
            >{{ link.label }} →</router-link
          >
        </div>
        <p>
          E-Mail: {{ status.email_configured ? 'Server hinterlegt' : 'noch nicht eingerichtet' }} ·
          LDAP: {{ status.ldap_enabled ? 'aktiv' : 'aus' }} · Single Sign-On:
          {{ status.oidc_enabled ? 'aktiv' : 'aus' }} · Push:
          {{ status.push_enabled ? 'aktiv' : 'aus' }}
        </p>
        <p>
          Domain, Datenbank, Redis, TLS, Hauptschlüssel und Backups bleiben Aufgabe der
          Hostadministration.
        </p>
        <router-link to="/settings/catalog"
          >Alle Einstellungsfelder und Hostgrenzen ansehen →</router-link
        >
      </article>
      <div class="setup-actions">
        <Button
          label="Zurück"
          severity="secondary"
          outlined
          :disabled="step === 0"
          @click="step--"
        />
        <Button v-if="step < steps.length - 1" label="Weiter" @click="step++" />
        <Button v-else label="Einrichtungsstand neu prüfen" :loading="loading" @click="load" />
      </div>
    </template>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import { configurationApi, configurationError, type SetupStatus } from '@/api/configuration'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
const status = ref<SetupStatus | null>(null),
  loading = ref(false),
  error = ref(''),
  step = ref(0)
const steps = ['Organisation', 'Abteilungen', 'Konten und Rollen', 'Standards', 'Integrationen']
const masterLinks = [
  {
    to: '/settings/service',
    label: 'Dienstzeiten',
    permission: 'settings_manager.view_service_settings',
  },
  {
    to: '/settings/training',
    label: 'Übungszeiten und Bausteindauer',
    permission: 'settings_manager.view_general_settings',
  },
  {
    to: '/settings/member',
    label: 'Anwesenheitsregeln, Status und Ereignisarten',
    permission: 'settings_manager.view_member_settings',
  },
  { to: '/groups', label: 'Gruppen', permission: 'members.view_group' },
  {
    to: '/qualifications/types',
    label: 'Qualifikationsarten',
    permission: 'qualifications.view_qualificationtype',
  },
  {
    to: '/qualifications/specialtasks/types',
    label: 'Aufgabenarten',
    permission: 'qualifications.view_specialtasktype',
  },
  { to: '/training', label: 'Übungsvorlagen', permission: 'training.view_trainingsession' },
  { to: '/inventory', label: 'Inventarstammdaten und Lager', permission: 'inventory.view_item' },
  { to: '/orders', label: 'Bestellartikel und Statusablauf', permission: 'orders.view_order' },
  {
    to: '/settings/order',
    label: 'Bestellbenachrichtigungen',
    permission: 'settings_manager.view_order_settings',
  },
]
const permittedMasterLinks = computed(() =>
  masterLinks.filter(
    (link) =>
      auth.hasPerm(link.permission) ||
      (link.to.startsWith('/settings/') && auth.hasPerm('settings_manager.view_all_settings')),
  ),
)
const integrationLinks = [
  { to: '/settings/email', label: 'E-Mail-Versand' },
  { to: '/settings/email-templates', label: 'E-Mail-Vorlagen' },
  { to: '/settings/ldap', label: 'Verzeichnisanmeldung' },
  { to: '/settings/oidc', label: 'Single Sign-On' },
  { to: '/settings/member', label: 'Externe Mitgliedersynchronisation' },
  { to: '/settings/push', label: 'Push einrichten' },
  { to: '/settings/security', label: 'Sitzungsrichtlinien' },
]
async function load() {
  loading.value = true
  error.value = ''
  try {
    status.value = (await configurationApi.setup()).data
  } catch (err) {
    error.value = configurationError(err)
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<style scoped>
.setup-section {
  max-width: 850px;
  padding: 1.5rem;
}
p {
  line-height: 1.65;
}
.setup-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 1.5rem 0;
}
.setup-steps button {
  min-height: 44px;
  border: 1px solid var(--p-form-field-border-color);
  border-radius: 8px;
  background: var(--p-form-field-background);
  color: var(--jf-color-text);
  padding: 0.6rem 0.8rem;
  cursor: pointer;
}
.setup-steps button[aria-current] {
  background: var(--jf-color-selected);
  color: var(--jf-color-selected-text);
  border-color: var(--jf-color-primary);
  font-weight: 600;
}
article {
  min-height: 240px;
  padding: 1.25rem;
  background: var(--p-content-background);
  border: 1px solid var(--p-content-border-color);
  border-radius: 12px;
}
.setup-links {
  display: grid;
  gap: 0.6rem;
}
.setup-links a {
  padding: 0.3rem 0;
  min-height: 44px;
}
.setup-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1.5rem;
}
</style>
