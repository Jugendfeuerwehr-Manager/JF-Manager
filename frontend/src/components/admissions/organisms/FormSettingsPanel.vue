<template>
  <form class="settings" @submit.prevent="save">
    <div class="settings__main">
      <section class="settings__card" aria-labelledby="set-scope-title">
        <h2 id="set-scope-title">Gilt für</h2>
        <div class="settings__options">
          <label class="settings__option" :class="{ 'settings__option--on': local.department === null }">
            <input v-model="scope" type="radio" value="organisation" class="adm-check" :disabled="!canEdit" />
            <span>
              <strong>Ganze Organisation</strong>
              <span class="settings__sub">Ein Formular für alle Abteilungen. Wohin ein Antrag geht, entscheidet der Voucher oder die Auswahl im Formular.</span>
            </span>
          </label>
          <label class="settings__option" :class="{ 'settings__option--on': local.department !== null }">
            <input v-model="scope" type="radio" value="department" class="adm-check" :disabled="!canEdit || ownDepartment === null" />
            <span>
              <strong>Eine Abteilung</strong>
              <span class="settings__sub">Alle Anträge landen bei der gewählten Abteilung.</span>
            </span>
          </label>
        </div>
        <AdmField v-if="local.department !== null" input-id="set-department" label="Abteilung">
          <select id="set-department" v-model="local.department" class="adm-input" :disabled="!canEdit">
            <option v-for="department in departments" :key="department.id" :value="department.id">{{ department.name }}</option>
          </select>
        </AdmField>
      </section>

      <section class="settings__card" aria-labelledby="set-access-title">
        <h2 id="set-access-title">Zugang</h2>
        <div class="settings__options">
          <label class="settings__option" :class="{ 'settings__option--on': local.access === 'voucher' }">
            <input v-model="local.access" type="radio" value="voucher" class="adm-check" :disabled="!canEdit" />
            <span>
              <strong>Nur mit Voucher</strong>
              <span class="settings__sub">Jede*r Interessent*in bekommt einen Einmal-Code. Der Voucher legt die Abteilung fest.</span>
            </span>
          </label>
          <label class="settings__option" :class="{ 'settings__option--on': local.access === 'public' }">
            <input v-model="local.access" type="radio" value="public" class="adm-check" :disabled="!canEdit" />
            <span>
              <strong>Öffentlich und mit Voucher</strong>
              <span class="settings__sub">Ein Link für Website und Aushang. Voucher funktionieren weiter.</span>
            </span>
          </label>
        </div>

        <fieldset v-if="local.access === 'public' && local.department === null" class="settings__departments">
          <legend>Auswählbare Abteilungen im öffentlichen Formular</legend>
          <p class="settings__sub">Nur die angehakten Abteilungen werden öffentlich genannt. Die übrige Organisationsstruktur bleibt unsichtbar.</p>
          <label v-for="department in departments" :key="department.id" class="settings__check">
            <input v-model="local.public_departments" type="checkbox" :value="department.id" class="adm-check" :disabled="!canEdit" />
            {{ department.name }}
          </label>
          <p v-if="!local.public_departments.length" class="settings__warn">Ohne Auswahl kann niemand den öffentlichen Antrag absenden.</p>
        </fieldset>
      </section>

      <section class="settings__card" aria-labelledby="set-process-title">
        <h2 id="set-process-title">Formular und Ablauf</h2>
        <div class="settings__grid">
          <AdmField input-id="set-title" label="Titel" required>
            <input id="set-title" v-model="local.title" class="adm-input" required maxlength="200" :disabled="!canEdit" />
          </AdmField>
          <AdmField input-id="set-body" label="Entscheidet" hint="z. B. Jugendausschuss">
            <input id="set-body" v-model="local.decision_body" class="adm-input" maxlength="100" :disabled="!canEdit" />
          </AdmField>
          <AdmField input-id="set-intro" label="Einleitung" hint="Erscheint oberhalb des Formulars." class="settings__wide">
            <textarea id="set-intro" v-model="local.intro" class="adm-input" :disabled="!canEdit"></textarea>
          </AdmField>
          <AdmField input-id="set-status" label="Stufe nach Übernahme" :hint="local.department === null ? 'Organisationsformulare: nur zentrale Stufen.' : 'Kategorien Antrag, Probezeit oder Aktiv.'">
            <select id="set-status" v-model="local.initial_status" class="adm-input" :disabled="!canEdit">
              <option :value="null">Keine Stufe</option>
              <option v-for="status in statusOptions" :key="status.id" :value="status.id">{{ status.name }}</option>
            </select>
          </AdmField>
          <AdmField input-id="set-signature" label="Unterschrift">
            <select id="set-signature" v-model="local.signature_mode" class="adm-input" :disabled="!canEdit">
              <option value="both">Digital und Ausdruck</option>
              <option value="digital">Nur digital</option>
              <option value="print">Ausdrucken und auf Papier</option>
            </select>
          </AdmField>
          <label class="settings__check settings__wide">
            <input v-model="local.is_active" type="checkbox" class="adm-check" :disabled="!canEdit" />
            Aktiv: nimmt neue Anträge an
          </label>
        </div>
      </section>

      <div>
        <AdmButton variant="primary" type="submit" icon="pi pi-check" :disabled="!canEdit">Einstellungen speichern</AdmButton>
      </div>
    </div>

    <aside class="settings__aside">
      <section class="settings__card" aria-labelledby="set-link-title">
        <h2 id="set-link-title">Öffentlicher Link</h2>
        <template v-if="publicUrl">
          <div class="settings__link">
            <!-- eslint-disable-next-line vue/no-v-html -- SVG generated locally by the qrcode package -->
            <div class="settings__qr" role="img" aria-label="QR-Code für den öffentlichen Link" v-html="qrSvg"></div>
            <div class="settings__link-text">
              <code>{{ publicUrl }}</code>
              <AdmButton icon="pi pi-copy" @click="copy">{{ copied ? 'Kopiert' : 'Kopieren' }}</AdmButton>
            </div>
          </div>
          <p class="settings__sub">
            Schutz vor Missbrauch: Anfragen je Gerät begrenzt, unsichtbares Prüffeld gegen Bots. Jeder Antrag wird trotzdem
            geprüft und beschlossen.
          </p>
          <p v-if="!form.current_version" class="settings__warn">Erst nach dem Veröffentlichen erreichbar.</p>
        </template>
        <p v-else class="settings__sub">
          Wähle „Öffentlich“ und speichere: Dann entsteht ein Link mit QR-Code für Website und Aushang.
        </p>
      </section>
      <section class="settings__card" aria-labelledby="set-voucher-title">
        <h2 id="set-voucher-title">Voucher</h2>
        <p class="settings__sub">
          Beim Erstellen eines Vouchers wählst du {{ form.department === null ? 'die Abteilung, an die der Antrag geht' : 'nichts weiter: der Antrag geht an diese Abteilung' }}.
          Vor- und Nachname lassen sich vorbelegen.
        </p>
        <RouterLink :to="{ name: 'admission-vouchers' }" class="settings__more">Voucher erstellen →</RouterLink>
      </section>
    </aside>
  </form>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import QRCode from 'qrcode'
import AdmButton from '../atoms/AdmButton.vue'
import AdmField from '../atoms/AdmField.vue'
import { useDepartmentsStore } from '@/stores/departments'
import { useMembersStore } from '@/stores/members'
import type { AdmissionForm, AdmissionFormUpdate } from '@/types/admissions'
import '../atoms/admInput.css'

interface Props {
  form: AdmissionForm
  canEdit: boolean
}

type Local = Required<Omit<AdmissionFormUpdate, 'draft_schema'>>

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'save', data: AdmissionFormUpdate): void }>()
const membersStore = useMembersStore()
const departmentsStore = useDepartmentsStore()

const local = reactive<Local>({
  title: '',
  intro: '',
  signature_mode: 'both',
  decision_body: '',
  initial_status: null,
  is_active: true,
  department: null,
  access: 'voucher',
  public_departments: []
})
const qrSvg = ref('')
const copied = ref(false)

const departments = computed(() => departmentsStore.departments.filter((department) => department.is_active !== false))
// Switching to "one department" picks the form's own or the first available one.
const ownDepartment = computed(() => props.form.department ?? departments.value[0]?.id ?? null)
const statusOptions = computed(() =>
  membersStore.statuses.filter(
    (status) =>
      ['applicant', 'trial', 'active'].includes(status.category) &&
      (status.department === null || status.department === local.department)
  )
)
const scope = computed({
  get: () => (local.department === null ? 'organisation' : 'department'),
  set: (value: string) => {
    local.department = value === 'organisation' ? null : ownDepartment.value
  }
})
const publicUrl = computed(() =>
  props.form.access === 'public' && props.form.public_slug
    ? `${window.location.origin}/aufnahme/f/${props.form.public_slug}`
    : ''
)

function load(form: AdmissionForm) {
  Object.assign(local, {
    title: form.title,
    intro: form.intro,
    signature_mode: form.signature_mode,
    decision_body: form.decision_body,
    initial_status: form.initial_status,
    is_active: form.is_active,
    department: form.department,
    access: form.access,
    public_departments: [...form.public_departments]
  })
}

function save() {
  emit('save', { ...local, public_departments: local.department === null ? local.public_departments : [] })
}

async function copy() {
  await navigator.clipboard.writeText(publicUrl.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}

watch(() => props.form, load, { immediate: true })
watch(
  publicUrl,
  async (url) => {
    qrSvg.value = url ? await QRCode.toString(url, { type: 'svg', errorCorrectionLevel: 'M', margin: 1 }) : ''
  },
  { immediate: true }
)
onMounted(() => {
  if (!membersStore.statuses.length) membersStore.fetchStatuses()
  if (!departmentsStore.departments.length) departmentsStore.fetchDepartments()
})
</script>

<style scoped>
.settings {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-3);
  align-items: flex-start;
}

.settings__main {
  flex: 999 1 34rem;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.settings__aside {
  flex: 1 1 18rem;
  min-width: 0;
  max-width: 24rem;
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-2);
}

.settings__card {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  padding: var(--jf-space-2-5, 1.25rem);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-lg);
  background: var(--jf-color-card);
}

.settings__card h2 {
  margin: 0;
  font-size: var(--jf-text-md);
}

.settings__options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
  gap: var(--jf-space-1);
}

.settings__option {
  display: flex;
  gap: var(--jf-space-1-5);
  align-items: flex-start;
  padding: var(--jf-space-1-5);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
  cursor: pointer;
}

.settings__option--on {
  border: 2px solid var(--jf-color-primary);
  background: var(--jf-color-selected);
}

.settings__sub {
  display: block;
  margin: 0.15rem 0 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.settings__warn {
  margin: 0;
  font-size: var(--jf-text-sm);
  color: var(--jf-color-warning);
}

.settings__departments {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  margin: 0;
  padding: var(--jf-space-1-5) var(--jf-space-2);
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-md);
}

.settings__departments legend {
  padding: 0 var(--jf-space-0-5);
  font-weight: var(--jf-weight-semibold);
}

.settings__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--jf-space-1-5);
}

.settings__wide {
  grid-column: 1 / -1;
}

.settings__check {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
}

.settings__link {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-1-5);
  align-items: flex-start;
}

.settings__qr {
  flex: none;
  width: 9rem;
  height: 9rem;
  padding: var(--jf-space-0-5);
  border-radius: var(--jf-radius-md);
  background: white;
}

.settings__qr :deep(svg) {
  width: 100%;
  height: 100%;
}

.settings__link-text {
  display: flex;
  flex-direction: column;
  align-self: stretch;
  gap: var(--jf-space-1);
  min-width: 0;
}

.settings__link-text code {
  padding: var(--jf-space-0-5) var(--jf-space-1);
  border-radius: var(--jf-radius-sm);
  background: var(--jf-color-ground);
  font-size: var(--jf-text-sm);
  overflow-wrap: anywhere;
}

.settings__more {
  font-weight: var(--jf-weight-semibold);
  color: var(--jf-color-primary);
}

@media (max-width: 640px) {
  .settings__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
