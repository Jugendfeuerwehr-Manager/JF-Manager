<template>
  <div class="adm-page">
    <RouterLink :to="{ name: 'admission-applications' }" class="detail__back"><i class="pi pi-arrow-left" aria-hidden="true"></i> Anträge</RouterLink>
    <p v-if="store.error" class="adm-page__error" role="alert">{{ store.error }}</p>
    <p v-if="store.loading && !application" class="adm-page__lead">Lade Antrag …</p>

    <template v-if="application">
      <header class="adm-page__head">
        <div>
          <h1>{{ application.applicant_name }}</h1>
          <p class="adm-page__lead">
            Eingereicht am {{ new Date(application.submitted_at).toLocaleString('de-DE') }} · {{ application.form_title }} (Version
            {{ application.form_version_number }})
          </p>
        </div>
        <span class="adm-badge" :data-state="application.status">{{ application.status_label }}</span>
      </header>

      <div class="detail__grid">
        <section class="adm-card detail__answers" aria-label="Antrag">
          <FormRenderer :schema="application.schema" :model-value="displayAnswers" disabled id-prefix="review" />
        </section>

        <aside class="detail__side">
          <section v-if="attachments.length" class="adm-card" aria-labelledby="attachments-title">
            <h2 id="attachments-title">Anlagen</h2>
            <ul class="detail__files">
              <li v-for="attachment in attachments" :key="attachment.key">
                <a :href="attachment.url" target="_blank" rel="noopener" class="detail__file">
                  <i class="pi pi-file-pdf" aria-hidden="true"></i>
                  <span>
                    <strong>{{ attachment.label }}</strong>
                    <span class="detail__hint">{{ attachment.name }}</span>
                  </span>
                </a>
              </li>
            </ul>
            <p class="detail__hint">Mit dem Antrag versiegelt; bei der Übernahme werden sie Anhänge am Mitglied.</p>
          </section>

          <section class="adm-card" aria-labelledby="seal-title">
            <h2 id="seal-title">Siegel</h2>
            <p class="detail__verdict" :data-ok="store.verification?.valid">
              <i :class="store.verification?.valid ? 'pi pi-verified' : 'pi pi-exclamation-triangle'" aria-hidden="true"></i>
              {{ store.verification?.valid ? 'Unverändert seit dem Einreichen' : 'Prüfung fehlgeschlagen' }}
            </p>
            <ul class="detail__seals">
              <li v-for="seal in store.verification?.seals ?? []" :key="seal.public_id">
                <span class="adm-badge" :data-state="seal.valid ? 'valid' : 'invalid'">{{ SEAL_LABELS[seal.kind] }}</span>
                {{ new Date(seal.sealed_at).toLocaleString('de-DE') }}
                <code class="detail__hash" :title="seal.seal_hash">{{ seal.public_id }}</code>
                <span v-if="!seal.current_key" class="detail__hint">älterer Schlüssel</span>
              </li>
            </ul>
            <AdmButton v-if="canExport" icon="pi pi-file-pdf" :loading="exporting" @click="exportPdf">Versiegelter Export (PDF)</AdmButton>
          </section>

          <section class="adm-card" aria-labelledby="decision-title">
            <h2 id="decision-title">Beschluss</h2>
            <ol v-if="application.decisions.length" class="detail__decisions">
              <li v-for="decision in application.decisions" :key="decision.id">
                <strong>{{ decision.outcome_label }}</strong> durch {{ decision.body }} am
                {{ new Date(`${decision.decided_on}T00:00:00`).toLocaleDateString('de-DE') }}
                <template v-if="decision.votes_yes !== null">
                  ({{ decision.votes_yes }} ja / {{ decision.votes_no ?? 0 }} nein / {{ decision.votes_abstain ?? 0 }} Enthaltung)
                </template>
                <p v-if="decision.note" class="detail__hint">{{ decision.note }}</p>
              </li>
            </ol>
            <form v-if="isOpen && canDecide" class="detail__form" @submit.prevent="decide">
              <AdmField input-id="d-outcome" label="Ergebnis">
                <select id="d-outcome" v-model="decision.outcome" class="adm-input">
                  <option value="approved">Aufnahme angenommen</option>
                  <option value="deferred">Zurückgestellt</option>
                  <option value="rejected">Abgelehnt</option>
                </select>
              </AdmField>
              <AdmField input-id="d-date" :label="`Beschluss ${application.decision_body} am`">
                <input id="d-date" v-model="decision.decided_on" type="date" class="adm-input" required />
              </AdmField>
              <div class="adm-grid-2">
                <AdmField input-id="d-yes" label="Ja"><input id="d-yes" v-model.number="decision.votes_yes" type="number" min="0" class="adm-input" /></AdmField>
                <AdmField input-id="d-no" label="Nein"><input id="d-no" v-model.number="decision.votes_no" type="number" min="0" class="adm-input" /></AdmField>
              </div>
              <AdmField input-id="d-note" label="Notiz">
                <textarea id="d-note" v-model="decision.note" class="adm-input"></textarea>
              </AdmField>
              <AdmButton variant="primary" type="submit" icon="pi pi-check" :loading="store.saving">Beschluss erfassen und versiegeln</AdmButton>
            </form>
            <p v-else-if="isOpen" class="detail__hint">Beschlüsse erfasst, wer das Recht dazu hat.</p>
          </section>

          <section v-if="application.status === 'approved' && canTakeOver" class="adm-card" aria-labelledby="takeover-title">
            <h2 id="takeover-title">In die Mitgliederverwaltung übernehmen</h2>
            <form class="detail__form" @submit.prevent="takeOver">
              <AdmField input-id="t-joined" label="Eintrittsdatum">
                <input id="t-joined" v-model="takeover.joined" type="date" class="adm-input" required />
              </AdmField>
              <fieldset v-for="(guardian, index) in guardians" :key="index" class="detail__guardian">
                <legend>{{ guardian.name }} {{ guardian.lastname }}</legend>
                <label class="detail__choice">
                  <input v-model="takeover.links[index]" type="radio" class="adm-check" :value="null" /> Neu anlegen
                </label>
                <label v-for="match in store.parentSuggestions[index] ?? []" :key="match.id" class="detail__choice">
                  <input v-model="takeover.links[index]" type="radio" class="adm-check" :value="match.id" />
                  Vorhandene*n verknüpfen: {{ match.name }} ({{ match.email }})
                </label>
              </fieldset>
              <label class="detail__choice">
                <input v-model="takeover.invite" type="checkbox" class="adm-check" /> Sorgeberechtigte ins Portal einladen
              </label>
              <AdmButton variant="primary" type="submit" icon="pi pi-user-plus" :loading="store.saving">Mitglied anlegen</AdmButton>
            </form>
          </section>

          <section v-if="application.member" class="adm-card">
            <h2>Übernommen</h2>
            <RouterLink :to="`/members/${application.member}`">Zum Mitglied</RouterLink>
          </section>
        </aside>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import AdmField from '@/components/admissions/atoms/AdmField.vue'
import FormRenderer from '@/components/admissions/organisms/FormRenderer.vue'
import '@/components/admissions/atoms/admInput.css'
import '@/components/admissions/atoms/admPage.css'
import { useAdmissionsStore } from '@/stores/admissions'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import type { AdmissionDecision, DecisionOutcome, SealCheck } from '@/types/admissions'
import { buildApplicationPdf, downloadPdf, imageAsDataUrl } from '@/utils/admissionPdf'

const SEAL_LABELS: Record<SealCheck['kind'], string> = {
  submission: 'Eingereicht',
  decision: 'Beschluss',
  export: 'Export',
  annual_report: 'Jahresmeldung'
}

const route = useRoute()
const router = useRouter()
const store = useAdmissionsStore()
const auth = useAuthStore()
const departments = useDepartmentsStore()
const id = Number(route.params.id)
const today = new Date().toISOString().slice(0, 10)
const exporting = ref(false)
const images = ref<Record<string, string>>({})

const decision = reactive({ outcome: 'approved' as DecisionOutcome, decided_on: today, votes_yes: null as number | null, votes_no: null as number | null, note: '' })
const takeover = reactive({ joined: today, links: [] as (number | null)[], invite: false })

const application = computed(() => (store.current?.id === id ? store.current : null))
const isOpen = computed(() => !!application.value && ['submitted', 'deferred'].includes(application.value.status))
const canDecide = computed(() => auth.hasPerm('admissions.record_decision'))
const canTakeOver = computed(() => auth.hasPerm('admissions.take_over_application') && auth.hasPerm('members.add_member'))
const canExport = computed(() => auth.hasPerm('admissions.export_application'))
const guardians = computed(() => {
  const app = application.value
  if (!app) return []
  const element = app.schema.pages.flatMap((p) => p.sections.flatMap((s) => s.elements)).find((e) => e.type === 'guardians')
  const rows = element?.key ? app.answers[element.key] : null
  return Array.isArray(rows) ? (rows as Record<string, string>[]) : []
})
const attachments = computed(() => {
  const app = application.value
  if (!app) return []
  return app.schema.pages
    .flatMap((page) => page.sections.flatMap((section) => section.elements))
    .filter((element) => element.type === 'attachment' && element.key && app.files[element.key])
    .map((element) => {
      const answer = app.answers[element.key!] as { name?: string } | undefined
      return { key: element.key!, label: element.label || 'Anlage', name: answer?.name ?? 'PDF', url: app.files[element.key!]!.url }
    })
})
// Files are referenced by key in the answers; show the loaded images instead.
const displayAnswers = computed(() => ({ ...(application.value?.answers ?? {}), ...images.value }))

async function loadImages() {
  const files = application.value?.files ?? {}
  const loaded: Record<string, string> = {}
  await Promise.all(
    Object.entries(files)
      .filter(([, file]) => file.kind !== 'attachment')
      .map(async ([key, file]) => {
        loaded[key] = await imageAsDataUrl(file.url).catch(() => '')
      })
  )
  images.value = loaded
}

async function decide() {
  const label = { approved: 'Annahme', deferred: 'Zurückstellung', rejected: 'Ablehnung' }[decision.outcome]
  if (!window.confirm(`${label} erfassen? Der Beschluss wird versiegelt und kann nicht mehr geändert werden.`)) return
  await store.decide(id, { ...decision }).catch(() => undefined)
}

async function takeOver() {
  const links = Object.fromEntries(takeover.links.map((parentId, index) => [String(index), parentId]))
  try {
    const memberId = await store.takeOver(id, { joined: takeover.joined, parent_links: links, invite_parents: takeover.invite })
    router.push({ path: `/members/${memberId}`, query: { ausweis: '1' } })
  } catch {
    // store.error is shown on the page
  }
}

function latestDecision(decisions: AdmissionDecision[]) {
  const last = decisions.at(-1)
  return last ? { ...last, recorded_by: last.recorded_by_name } : undefined
}

async function exportPdf() {
  exporting.value = true
  try {
    const data = await store.exportSealed(id)
    await downloadPdf(
      buildApplicationPdf({
        title: data.form_title,
        department: departments.departments.find((d) => d.id === data.department)?.name ?? '',
        schema: data.schema,
        answers: data.answers,
        images: images.value,
        signatureMode: data.signature_mode,
        submittedAt: data.submitted_at,
        applicantName: data.applicant_name,
        applicationNumber: data.id,
        fileHashes: Object.fromEntries(Object.entries(data.files).map(([key, file]) => [key, file.sha256])),
        decision: latestDecision(data.decisions),
        seal: { publicId: data.export_seal.public_id, sealHash: data.export_seal.seal_hash, label: `Versiegelter Export vom ${new Date(data.export_seal.sealed_at).toLocaleString('de-DE')}` },
        verifyUrl: `${window.location.origin}/aufnahme/pruefen/${data.export_seal.public_id}`
      }),
      `aufnahmeantrag-${id}.pdf`
    )
  } catch {
    // store.error is shown on the page
  } finally {
    exporting.value = false
  }
}

watch(application, (app) => {
  if (!app) return
  takeover.links = guardians.value.map((_, index) => store.parentSuggestions[index]?.[0]?.id ?? null)
  const approval = app.decisions.find((d) => d.outcome === 'approved')
  if (approval) takeover.joined = approval.decided_on
  loadImages()
})

onMounted(() => store.openApplication(id))
</script>

<style scoped>
.detail__back {
  color: var(--jf-color-text-muted);
  text-decoration: none;
}

.detail__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 22rem;
  gap: var(--jf-space-2);
  align-items: start;
}

.detail__side {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.detail__verdict {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  margin: 0 0 var(--jf-space-1);
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-danger);
}

.detail__verdict[data-ok='true'] {
  color: var(--jf-color-success);
}

.detail__seals,
.detail__decisions {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  margin: 0 0 var(--jf-space-1-5);
  padding: 0;
  list-style: none;
  font-size: var(--jf-text-sm);
}

.detail__hash {
  font-family: var(--jf-font-mono);
}

.detail__hint {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.detail__form {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
}

.detail__guardian {
  margin: 0;
  padding: var(--jf-space-1);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.detail__choice {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
}

@media (max-width: 1000px) {
  .detail__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

.detail__files {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1);
  margin: 0 0 var(--jf-space-1);
  padding: 0;
  list-style: none;
}

.detail__file {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  color: var(--jf-color-text);
  text-decoration: none;
  overflow-wrap: anywhere;
}

.detail__file:hover {
  border-color: var(--jf-color-primary);
}

.detail__file span {
  display: flex;
  flex-direction: column;
}
</style>
