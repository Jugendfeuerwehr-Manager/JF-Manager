<template>
  <main class="public">
    <div class="public__card">
      <!-- 1. Code entry -->
      <section v-if="!store.form && !store.result" aria-labelledby="code-title">
        <h1 id="code-title">Aufnahmeantrag</h1>
        <p class="public__lead">Gib den Code von deiner Einladung ein oder scanne den QR-Code.</p>
        <form class="public__code" @submit.prevent="openWithCode">
          <AdmField input-id="voucher-code" label="Code" :error="store.error ?? ''" hint="Beispiel: 7KQ4-M2XR-9PDA">
            <template #default="{ describedby }">
              <input
                id="voucher-code"
                v-model="codeInput"
                class="adm-input public__code-input"
                autocomplete="one-time-code"
                autocapitalize="characters"
                spellcheck="false"
                inputmode="text"
                :aria-describedby="describedby"
                :aria-invalid="!!store.error"
                required
              />
            </template>
          </AdmField>
          <AdmButton variant="primary" type="submit" :loading="store.loading" icon="pi pi-arrow-right">Weiter</AdmButton>
        </form>
      </section>

      <!-- 2. Form wizard -->
      <section v-else-if="store.form && !store.result" :aria-labelledby="'form-title'">
        <header class="public__head">
          <p class="public__department">{{ store.form.department }}</p>
          <h1 id="form-title">{{ store.form.title }}</h1>
          <p v-if="store.form.intro && page === 0" class="public__lead">{{ store.form.intro }}</p>
          <ol class="public__steps" aria-label="Fortschritt">
            <li
              v-for="(step, index) in store.form.schema.pages"
              :key="step.id"
              :class="{ 'public__step--done': index < page, 'public__step--current': index === page }"
              :aria-current="index === page ? 'step' : undefined"
            >
              <span class="public__step-number">{{ index + 1 }}</span>
              <span class="public__step-title">{{ step.title }}</span>
            </li>
          </ol>
        </header>

        <p v-if="store.error" class="public__error" role="alert">{{ store.error }}</p>

        <form novalidate @submit.prevent="next">
          <FormRenderer
            :schema="store.form.schema"
            :model-value="store.answers"
            :errors="errors"
            :page="page"
            :disabled="store.loading"
            id-prefix="apply"
            @update:model-value="store.setAnswers"
          />
          <div class="public__nav">
            <AdmButton v-if="page > 0" icon="pi pi-arrow-left" :disabled="store.loading" @click="back">Zurück</AdmButton>
            <span v-else></span>
            <AdmButton v-if="!isLast" variant="primary" type="submit" icon="pi pi-arrow-right">Weiter</AdmButton>
            <AdmButton v-else variant="primary" type="submit" icon="pi pi-send" :loading="store.loading">Antrag absenden</AdmButton>
          </div>
        </form>
        <p class="public__fine">
          Der Antrag wird nach dem Absenden versiegelt und kann danach nicht mehr verändert werden. Über die Aufnahme
          entscheidet {{ store.form.decision_body || 'die Leitung' }}.
        </p>
      </section>

      <!-- 3. Done -->
      <section v-else-if="store.result" aria-labelledby="done-title" class="public__done">
        <i class="pi pi-check-circle public__done-icon" aria-hidden="true"></i>
        <h1 id="done-title">Vielen Dank!</h1>
        <p>
          Der Aufnahmeantrag für <strong>{{ store.result.applicant_name }}</strong> ist eingegangen und wurde versiegelt.
          Über die Aufnahme entscheidet {{ submittedForm?.decision_body || 'die Leitung' }}; du hörst von uns.
        </p>
        <p v-if="submittedForm?.signature_mode !== 'digital'" class="public__note">
          Bitte lade den Antrag als PDF herunter, drucke ihn aus und gib ihn unterschrieben ab.
        </p>
        <dl class="public__seal">
          <dt>Siegel-ID</dt>
          <dd>{{ store.result.seal.public_id }}</dd>
          <dt>Eingegangen</dt>
          <dd>{{ new Date(store.result.submitted_at).toLocaleString('de-DE') }}</dd>
        </dl>
        <AdmButton variant="primary" icon="pi pi-file-pdf" :loading="pdfBusy" @click="downloadApplication">Antrag als PDF</AdmButton>
        <p v-if="pdfError" class="public__error" role="alert">{{ pdfError }}</p>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import AdmField from '@/components/admissions/atoms/AdmField.vue'
import FormRenderer from '@/components/admissions/organisms/FormRenderer.vue'
import '@/components/admissions/atoms/admInput.css'
import { usePublicAdmissionStore } from '@/stores/publicAdmission'
import type { FormElement, PublicAdmissionForm } from '@/types/admissions'
import { buildApplicationPdf, downloadPdf } from '@/utils/admissionPdf'
import { ageOn, allElements, isVisible } from '@/utils/admissionSchema'

const store = usePublicAdmissionStore()
const codeInput = ref('')
const page = ref(0)
const localErrors = ref<Record<string, string>>({})
const submittedForm = ref<PublicAdmissionForm | null>(null)
const submittedAnswers = ref<Record<string, unknown>>({})
const pdfBusy = ref(false)
const pdfError = ref('')

const isLast = computed(() => !!store.form && page.value >= store.form.schema.pages.length - 1)
const errors = computed(() => ({ ...store.fieldErrors, ...localErrors.value }))

function age() {
  const schema = store.form?.schema
  const birthday = schema ? allElements(schema).find((element) => element.target === 'member.birthday') : undefined
  const value = birthday?.key ? store.answers[birthday.key] : null
  return ageOn(typeof value === 'string' ? value : null)
}

function isEmpty(element: FormElement, value: unknown) {
  if (element.type === 'guardians') return !Array.isArray(value) || value.length < Math.max(element.min ?? 1, 1)
  if (['checkbox', 'legal_ack', 'consent'].includes(element.type)) return value !== true
  return value === undefined || value === null || value === ''
}

/** Quick check of the current page; the server checks everything again. */
function checkPage(): boolean {
  const current = store.form?.schema.pages[page.value]
  if (!current) return true
  const found: Record<string, string> = {}
  const currentAge = age()
  for (const element of current.sections.flatMap((section) => section.elements)) {
    if (!element.key || !element.required) continue
    if (!isVisible(element.visible_if, store.answers, currentAge)) continue
    if (isEmpty(element, store.answers[element.key])) {
      found[element.key] = element.type === 'checkbox' || element.type === 'legal_ack' || element.type === 'consent'
        ? 'Bitte bestätigen.'
        : 'Bitte ausfüllen.'
    }
  }
  localErrors.value = found
  return !Object.keys(found).length
}

function scrollTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function next() {
  if (!checkPage()) return
  if (!isLast.value) {
    page.value++
    scrollTop()
    return
  }
  submittedForm.value = store.form
  submittedAnswers.value = { ...store.answers }
  try {
    await store.submit()
    scrollTop()
  } catch {
    jumpToFirstError()
  }
}

function back() {
  localErrors.value = {}
  page.value = Math.max(page.value - 1, 0)
  scrollTop()
}

function jumpToFirstError() {
  const schema = store.form?.schema
  const keys = Object.keys(store.fieldErrors)
  if (!schema || !keys.length) return
  const index = schema.pages.findIndex((candidate) =>
    candidate.sections.some((section) => section.elements.some((element) => element.key && keys.includes(element.key)))
  )
  if (index >= 0) page.value = index
  scrollTop()
}

async function openWithCode() {
  await store.open(codeInput.value)
  page.value = 0
}

async function downloadApplication() {
  const form = submittedForm.value
  const result = store.result
  if (!form || !result) return
  pdfBusy.value = true
  pdfError.value = ''
  const images = Object.fromEntries(
    Object.entries(submittedAnswers.value).filter((entry): entry is [string, string] =>
      typeof entry[1] === 'string' && entry[1].startsWith('data:image/')
    )
  )
  try {
    await downloadPdf(
      buildApplicationPdf({
        title: form.title,
        department: form.department,
        schema: form.schema,
        answers: submittedAnswers.value,
        images,
        signatureMode: form.signature_mode,
        submittedAt: result.submitted_at,
        seal: { publicId: result.seal.public_id, sealHash: result.seal.seal_hash, label: 'Versiegelt beim Einreichen' },
        verifyUrl: `${window.location.origin}/aufnahme/pruefen/${result.seal.public_id}`
      }),
      `aufnahmeantrag-${result.seal.public_id}.pdf`
    )
  } catch {
    pdfError.value = 'Das PDF konnte nicht erstellt werden.'
  } finally {
    pdfBusy.value = false
  }
}

onMounted(() => {
  store.reset()
  // The QR code carries the code in the fragment, which the browser never sends to the server.
  const fromHash = new URLSearchParams(window.location.hash.slice(1)).get('code')
  if (!fromHash) return
  window.history.replaceState(null, '', window.location.pathname)
  codeInput.value = fromHash
  openWithCode()
})
</script>

<style scoped>
.public {
  min-height: 100vh;
  padding: var(--jf-space-3) var(--jf-space-2);
  background: var(--jf-color-ground);
  color: var(--jf-color-text);
  font-family: var(--jf-font-sans);
}

.public__card {
  max-width: 44rem;
  margin: 0 auto;
  padding: var(--jf-space-3);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
  box-shadow: var(--jf-shadow-md);
}

.public h1 {
  margin: 0 0 var(--jf-space-1);
  font-size: var(--jf-text-2xl);
  line-height: var(--jf-leading-tight);
}

.public__department {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.public__lead,
.public__fine {
  color: var(--jf-color-text-muted);
}

.public__fine {
  margin-top: var(--jf-space-3);
  font-size: var(--jf-text-sm);
}

.public__code {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.public__code-input {
  font-family: var(--jf-font-mono);
  font-size: var(--jf-text-lg);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.public__steps {
  display: flex;
  gap: var(--jf-space-1);
  margin: var(--jf-space-2) 0;
  padding: 0;
  list-style: none;
  overflow-x: auto;
}

.public__steps li {
  display: flex;
  align-items: center;
  gap: var(--jf-space-0-5);
  flex-shrink: 0;
  color: var(--jf-color-text-muted);
  font-size: var(--jf-text-sm);
}

.public__step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.6rem;
  height: 1.6rem;
  border: 1px solid var(--jf-color-border);
  border-radius: 50%;
}

.public__step--current {
  color: var(--jf-color-text);
  font-weight: var(--jf-weight-semibold);
}

.public__step--current .public__step-number,
.public__step--done .public__step-number {
  border-color: var(--jf-color-primary);
  background: var(--jf-color-primary);
  color: var(--jf-color-on-primary);
}

.public__nav {
  display: flex;
  justify-content: space-between;
  gap: var(--jf-space-1);
  margin-top: var(--jf-space-3);
}

.public__error {
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-danger-surface);
  color: var(--jf-color-danger);
}

.public__note {
  padding: var(--jf-space-1) var(--jf-space-1-5);
  border-radius: var(--jf-radius-md);
  background: var(--jf-color-warning-surface);
  color: var(--jf-color-warning);
}

.public__done {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--jf-space-1-5);
}

.public__done-icon {
  font-size: 2.5rem;
  color: var(--jf-color-success);
}

.public__seal {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--jf-space-0-5) var(--jf-space-2);
  margin: 0;
}

.public__seal dt {
  color: var(--jf-color-text-muted);
}

.public__seal dd {
  margin: 0;
  font-family: var(--jf-font-mono);
}

@media (max-width: 480px) {
  .public {
    padding: var(--jf-space-1);
  }

  .public__card {
    padding: var(--jf-space-2);
  }

  .public__step-title {
    display: none;
  }

  .public__step--current .public__step-title {
    display: inline;
  }
}
</style>
