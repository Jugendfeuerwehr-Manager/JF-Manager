<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Message from 'primevue/message'
import PortalEmptyCard from '@/components/portal/PortalEmptyCard.vue'
import { usePortalConsentsStore } from '@/stores/portalConsents'
import type { PortalConsentEntry } from '@/types/privacy'

const store = usePortalConsentsStore()
/** ``member:kind`` whose withdrawal waits for confirmation. */
const confirming = ref<string | null>(null)

onMounted(() => { void store.load() })

const dateFormat = new Intl.DateTimeFormat('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
const day = (iso: string) => dateFormat.format(new Date(iso))

function stateLine(entry: PortalConsentEntry | null | undefined) {
  if (!entry) return 'Noch nicht erteilt'
  const by = entry.recorded_by_name ? ` von ${entry.recorded_by_name}` : ''
  return entry.status === 'granted' ? `Erteilt am ${day(entry.recorded_at)}${by}` : `Widerrufen am ${day(entry.recorded_at)}${by}`
}

async function grant(member: number, kind: string) {
  await store.change(member, kind, 'granted')
}

async function withdraw(member: number, kind: string) {
  if (await store.change(member, kind, 'withdrawn')) confirming.value = null
}
</script>

<template>
  <div class="portal-consents">
    <header class="intro">
      <h1>Einwilligungen</h1>
      <p>
        Hier entscheidest du für jedes Kind, wozu du einwilligst. Du kannst eine Einwilligung jederzeit widerrufen;
        das gilt ab dem Widerruf. Jede Änderung wird mit Datum protokolliert, und die Jugendleitung wird informiert.
      </p>
    </header>

    <Message v-if="store.error" severity="error" :closable="false">{{ store.error }}</Message>
    <p v-if="store.loading && !store.overview.people.length" class="muted">Einwilligungen werden geladen …</p>

    <PortalEmptyCard v-else-if="!store.overview.kinds.length" icon="pi pi-check-square" title="Keine Einwilligungen">
      Deine Organisation fragt im Portal derzeit keine Einwilligungen ab.
    </PortalEmptyCard>

    <section v-for="person in store.overview.people" :key="person.member_id" class="card" :aria-labelledby="`consents-${person.member_id}`">
      <h2 :id="`consents-${person.member_id}`">{{ person.name }}</h2>
      <ul class="kinds">
        <li v-for="kind in store.overview.kinds" :key="kind.slug" class="kind">
          <div class="kind__text">
            <span class="kind__label">{{ kind.label }}</span>
            <p v-if="kind.description" class="kind__wording">{{ kind.description }}</p>
            <span
              class="kind__state"
              :class="`kind__state--${person.consents[kind.slug]?.status ?? 'open'}`"
            >
              <i
                :class="person.consents[kind.slug]?.status === 'granted' ? 'pi pi-check-circle' : person.consents[kind.slug] ? 'pi pi-times-circle' : 'pi pi-circle'"
                aria-hidden="true"
              ></i>{{ stateLine(person.consents[kind.slug]) }}
            </span>
          </div>

          <div class="kind__actions">
            <template v-if="person.consents[kind.slug]?.status === 'granted'">
              <template v-if="confirming === `${person.member_id}:${kind.slug}`">
                <span class="kind__confirm">Wirklich widerrufen?</span>
                <Button
                  label="Widerrufen"
                  severity="danger"
                  size="small"
                  class="touch"
                  :loading="store.saving === `${person.member_id}:${kind.slug}`"
                  @click="withdraw(person.member_id, kind.slug)"
                />
                <Button label="Abbrechen" severity="secondary" size="small" text class="touch" @click="confirming = null" />
              </template>
              <Button
                v-else
                label="Widerrufen"
                icon="pi pi-undo"
                severity="secondary"
                size="small"
                outlined
                class="touch"
                :aria-label="`${kind.label} für ${person.name} widerrufen`"
                @click="confirming = `${person.member_id}:${kind.slug}`"
              />
            </template>
            <Button
              v-else
              label="Einwilligen"
              icon="pi pi-check"
              size="small"
              class="touch"
              :aria-label="`${kind.label} für ${person.name} erteilen`"
              :loading="store.saving === `${person.member_id}:${kind.slug}`"
              @click="grant(person.member_id, kind.slug)"
            />
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.portal-consents { display: flex; flex-direction: column; gap: 1rem; min-width: 0; }
.intro h1 { margin: 0 0 4px; font-size: 20px; font-weight: 700; }
.intro p, .muted { margin: 0; font-size: 14px; color: var(--p-text-muted-color); }
.card { padding: 14px; border-radius: 14px; background: var(--p-content-background); border: 1px solid var(--p-content-border-color); min-width: 0; }
.card h2 { margin: 0 0 8px; font-size: 16px; font-weight: 650; }
.kinds { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.kind { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 0; border-top: 1px solid var(--p-content-border-color); }
.kind:first-child { border-top: none; padding-top: 4px; }
.kind__text { display: flex; flex-direction: column; gap: 4px; flex: 1 1 16rem; min-width: 0; }
.kind__label { font-weight: 600; }
.kind__wording { margin: 0; font-size: 13px; color: var(--p-text-muted-color); white-space: pre-line; }
.kind__state { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; }
.kind__state--granted { color: var(--p-green-700); }
.kind__state--withdrawn { color: var(--p-red-700); }
.kind__state--open { color: var(--p-text-muted-color); }
.kind__actions { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.kind__confirm { font-size: 13px; font-weight: 600; }
.touch { min-height: 44px; }
:global(.app-dark) .kind__state--granted { color: var(--p-green-300); }
:global(.app-dark) .kind__state--withdrawn { color: var(--p-red-300); }
</style>
