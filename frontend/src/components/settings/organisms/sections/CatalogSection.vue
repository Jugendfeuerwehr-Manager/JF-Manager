<template>
  <section class="catalog-section">
    <router-link to="/settings">← Einstellungen</router-link>
    <h2>Einstellungsübersicht</h2>
    <p>
      Fachliche Einstellungen werden in der Datenbank gespeichert. Geheimnisse sind verschlüsselt
      und werden nicht angezeigt. Hier findest du die Herkunft und Regeln jedes Feldes.
    </p>
    <p v-if="loading" role="status">Übersicht wird geladen …</p>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Button v-if="error" label="Erneut laden" @click="load" />
    <template v-if="catalog">
      <details v-for="(category, name) in catalog.categories" :key="name" class="catalog-category">
        <summary>
          {{ category.label }} · {{ category.can_change ? 'Bearbeitbar' : 'Nur ansehen' }}
        </summary>
        <router-link :to="`/settings/${name}`">Einstellungen öffnen →</router-link>
        <article v-for="(field, key) in category.fields" :key="key">
          <h3>{{ field.label }}</h3>
          <p>
            {{
              field.storage === 'derived'
                ? 'Abgeleiteter Wert'
                : field.storage.includes('encrypted')
                  ? 'Verschlüsselt gespeichert'
                  : 'Datenbank'
            }}
            · {{ source(field.source) }}<template v-if="field.locked"> · Gesperrt</template>
          </p>
          <p>
            Wirksam: {{ effective(field.effective) }}.
            {{
              field.secret
                ? 'Nur schreiben; gespeicherter Wert bleibt verborgen.'
                : field.validation
            }}
          </p>
          <p v-if="field.min != null || field.max != null || field.max_length">
            Grenzen: <template v-if="field.min != null">mindestens {{ field.min }} </template
            ><template v-if="field.max != null">höchstens {{ field.max }} </template
            ><template v-if="field.max_length">bis {{ field.max_length }} Zeichen</template>
          </p>
        </article>
        <details>
          <summary>Technische Berechtigungen</summary>
          <p>Lesen: {{ category.view_permission }} · Ändern: {{ category.change_permission }}</p>
        </details>
      </details>
      <div v-if="catalog.host.length" class="host-boundary">
        <h3>Am Host verwalten</h3>
        <p>
          Diese Einstellungen erfordern Zugriff auf die Installation und werden nicht in diesem
          Formular geändert.
        </p>
        <p v-for="field in catalog.host" :key="field.label">
          <strong>{{ field.label }}</strong> · {{ field.permission }} · {{ field.effective }}
        </p>
      </div>
    </template>
  </section>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import {
  configurationApi,
  configurationError,
  type ConfigurationCatalog,
} from '@/api/configuration'
const catalog = ref<ConfigurationCatalog | null>(null),
  loading = ref(false),
  error = ref('')
const source = (value: string) =>
  ({
    database: 'Organisationseinstellung',
    environment: 'Hostkonfiguration',
    default: 'Standardwert',
    computed: 'Abgeleiteter Wert',
  })[value] || value
const effective = (value: string) =>
  ({ next_session_check: 'Nächste Sitzungsprüfung', next_push_operation: 'Nächster Push-Vorgang' })[
    value
  ] || value
async function load() {
  loading.value = true
  error.value = ''
  try {
    catalog.value = (await configurationApi.catalog()).data
  } catch (err) {
    error.value = configurationError(err)
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<style scoped>
.catalog-section {
  max-width: 900px;
  padding: 1.5rem;
}
p {
  line-height: 1.6;
}
.catalog-category {
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid var(--p-content-border-color);
  border-radius: 8px;
}
summary {
  cursor: pointer;
  min-height: 44px;
  font-weight: 600;
}
article {
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--p-content-border-color);
}
h3 {
  font-size: 1rem;
  margin-bottom: 0.3rem;
}
.host-boundary {
  margin-top: 2rem;
}
</style>
