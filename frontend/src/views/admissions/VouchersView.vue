<template>
  <div class="adm-page">
    <header class="adm-page__head">
      <div>
        <h1>Voucher</h1>
        <p class="adm-page__lead">Einmal-Codes für Interessierte. Der Code wird nur direkt nach dem Erstellen angezeigt.</p>
      </div>
      <AdmButton v-if="canCreate" variant="primary" icon="pi pi-qrcode" @click="openCreate">Voucher erstellen</AdmButton>
    </header>

    <p v-if="store.error" class="adm-page__error" role="alert">{{ store.error }}</p>

    <div class="adm-table-wrap">
      <table class="adm-table">
        <caption class="sr-only">Erstellte Voucher</caption>
        <thead>
          <tr>
            <th scope="col">Für</th>
            <th scope="col">Formular</th>
            <th scope="col">Code-Ende</th>
            <th scope="col">Status</th>
            <th scope="col">Gültig bis</th>
            <th scope="col"><span class="sr-only">Aktionen</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!store.vouchers.length">
            <td colspan="6" class="adm-table__empty">{{ store.loading ? 'Lade …' : 'Noch keine Voucher.' }}</td>
          </tr>
          <tr v-for="voucher in store.vouchers" :key="voucher.id">
            <td>{{ voucher.label || '–' }}</td>
            <td>{{ voucher.form_title }}</td>
            <td><code>…{{ voucher.code_hint }}</code></td>
            <td><span class="adm-badge" :data-state="voucher.state">{{ STATE_LABELS[voucher.state] }}</span></td>
            <td>{{ formatDate(voucher.expires_at) }}</td>
            <td class="adm-table__actions">
              <RouterLink v-if="voucher.application" :to="{ name: 'admission-application', params: { id: voucher.application } }">Antrag</RouterLink>
              <AdmButton v-else-if="voucher.state === 'open' && canRevoke" variant="danger" icon="pi pi-ban" @click="revoke(voucher.id)">Widerrufen</AdmButton>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <dialog ref="dialog" class="adm-dialog" aria-labelledby="voucher-title" @close="created = null">
      <form v-if="!created" class="adm-dialog__body" @submit.prevent="create">
        <h2 id="voucher-title">Voucher erstellen</h2>
        <AdmField input-id="v-form" label="Formular" required>
          <select id="v-form" v-model.number="draft.form" class="adm-input" required>
            <option v-for="form in publishedForms" :key="form.id" :value="form.id">{{ form.title }}</option>
          </select>
        </AdmField>
        <AdmField
          v-if="selectedForm?.department === null"
          input-id="v-department"
          label="Antrag geht an"
          hint="Das Formular gilt für die ganze Organisation; der Voucher legt die Abteilung fest."
          required
        >
          <select id="v-department" v-model="draft.department" class="adm-input" required>
            <option :value="null" disabled>Abteilung wählen</option>
            <option v-for="department in departments.departments" :key="department.id" :value="department.id">
              {{ department.name }}
            </option>
          </select>
        </AdmField>
        <p v-if="!publishedForms.length" class="adm-page__lead">Zuerst ein Formular veröffentlichen.</p>
        <div class="adm-grid-2">
          <AdmField input-id="v-first" label="Vorname" hint="Wird im Formular vorausgefüllt.">
            <input id="v-first" v-model="draft.vorname" class="adm-input" maxlength="100" />
          </AdmField>
          <AdmField input-id="v-last" label="Nachname">
            <input id="v-last" v-model="draft.nachname" class="adm-input" maxlength="100" />
          </AdmField>
        </div>
        <AdmField input-id="v-days" label="Gültig (Tage)">
          <input id="v-days" v-model.number="draft.valid_days" type="number" min="1" max="365" class="adm-input" />
        </AdmField>
        <div class="adm-dialog__actions">
          <AdmButton variant="ghost" @click="dialog?.close()">Abbrechen</AdmButton>
          <AdmButton variant="primary" type="submit" icon="pi pi-check" :loading="store.saving" :disabled="!draft.form || (selectedForm?.department === null && !draft.department)">Erstellen</AdmButton>
        </div>
      </form>

      <section v-else class="adm-dialog__body" aria-live="polite">
        <h2 id="voucher-title">Voucher für {{ created.label || 'neues Mitglied' }}</h2>
        <!-- QR markup is generated locally by the qrcode library from our own URL -->
        <!-- eslint-disable-next-line vue/no-v-html -->
        <div class="voucher__qr" v-html="qrSvg"></div>
        <p class="voucher__code">{{ created.code }}</p>
        <p class="adm-page__lead">
          Der Code ist nur jetzt sichtbar. Karte drucken oder den QR-Code direkt scannen lassen. Gültig bis
          {{ formatDate(created.expires_at) }}.
        </p>
        <div class="adm-dialog__actions">
          <AdmButton icon="pi pi-copy" @click="copyLink">{{ copied ? 'Kopiert' : 'Link kopieren' }}</AdmButton>
          <AdmButton variant="primary" icon="pi pi-print" @click="printCard">Karte als PDF</AdmButton>
          <AdmButton variant="ghost" @click="dialog?.close()">Fertig</AdmButton>
        </div>
      </section>
    </dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import QRCode from 'qrcode'
import AdmButton from '@/components/admissions/atoms/AdmButton.vue'
import AdmField from '@/components/admissions/atoms/AdmField.vue'
import '@/components/admissions/atoms/admInput.css'
import '@/components/admissions/atoms/admPage.css'
import { useAdmissionFormsStore } from '@/stores/admissionForms'
import { useAdmissionsStore } from '@/stores/admissions'
import { useAuthStore } from '@/stores/auth'
import { useDepartmentsStore } from '@/stores/departments'
import type { CreatedVoucher, VoucherState } from '@/types/admissions'
import { buildVoucherCardPdf, downloadPdf } from '@/utils/admissionPdf'

const STATE_LABELS: Record<VoucherState, string> = { open: 'Offen', used: 'Eingelöst', expired: 'Abgelaufen', revoked: 'Widerrufen' }

const store = useAdmissionsStore()
const formsStore = useAdmissionFormsStore()
const auth = useAuthStore()
const departments = useDepartmentsStore()

const dialog = ref<HTMLDialogElement | null>(null)
const created = ref<CreatedVoucher | null>(null)
const qrSvg = ref('')
const copied = ref(false)
const draft = reactive<{ form: number; department: number | null; vorname: string; nachname: string; valid_days: number }>({
  form: 0,
  department: null,
  vorname: '',
  nachname: '',
  valid_days: 60
})

const canCreate = computed(() => auth.hasPerm('admissions.add_admissionvoucher'))
const canRevoke = computed(() => auth.hasPerm('admissions.change_admissionvoucher'))
const publishedForms = computed(() => formsStore.forms.filter((form) => form.current_version && form.is_active))
const selectedForm = computed(() => publishedForms.value.find((form) => form.id === draft.form))

const formatDate = (iso: string) => new Date(iso).toLocaleDateString('de-DE')
const voucherUrl = (code: string) => `${window.location.origin}/aufnahme#code=${encodeURIComponent(code)}`

function openCreate() {
  draft.form = publishedForms.value[0]?.id ?? 0
  draft.department = departments.activeDepartmentId ?? null
  draft.vorname = ''
  draft.nachname = ''
  dialog.value?.showModal()
}

async function create() {
  try {
    const department = selectedForm.value?.department === null ? draft.department : null
    created.value = await store.createVoucher({ ...draft, department })
    qrSvg.value = await QRCode.toString(voucherUrl(created.value.code), { type: 'svg', errorCorrectionLevel: 'M', margin: 2 })
    copied.value = false
  } catch {
    // store.error is shown on the page
  }
}

async function copyLink() {
  if (!created.value) return
  await navigator.clipboard.writeText(voucherUrl(created.value.code))
  copied.value = true
}

async function printCard() {
  if (!created.value) return
  const form = formsStore.forms.find((candidate) => candidate.id === created.value?.form)
  await downloadPdf(
    buildVoucherCardPdf({
      department: departments.departments.find((department) => department.id === created.value?.department)?.name ?? '',
      formTitle: form?.title ?? 'Aufnahmeantrag',
      code: created.value.code,
      url: voucherUrl(created.value.code),
      label: created.value.label,
      expiresAt: created.value.expires_at
    }),
    `aufnahme-code-${created.value.code_hint}.pdf`
  )
}

async function revoke(id: number) {
  if (!window.confirm('Voucher widerrufen? Der Code funktioniert danach nicht mehr.')) return
  await store.revokeVoucher(id).catch(() => undefined)
}

onMounted(() => {
  store.fetchVouchers()
  formsStore.fetchForms()
})
</script>

<style scoped>
.voucher__qr {
  width: 220px;
  margin: 0 auto;
}

.voucher__code {
  margin: 0;
  text-align: center;
  font-family: var(--jf-font-mono);
  font-size: var(--jf-text-2xl);
  font-weight: var(--jf-weight-bold);
  letter-spacing: 0.08em;
}
</style>
