<template>
  <Dialog
    :visible="visible"
    modal
    header="DJF-Mitgliedsausweis drucken"
    class="idcard-dialog"
    :style="{ width: 'min(76rem, calc(100vw - 2rem))' }"
    @update:visible="(value: boolean) => emit('update:visible', value)"
  >
    <p class="idcard__lead">
      Gedruckt werden nur die Angaben, nicht der Rahmen: Lege den vorgedruckten DJF-Ausweis in den Drucker und wähle im
      Druckdialog <strong>Tatsächliche Größe (100 %)</strong>. Die Angaben lassen sich hier noch anpassen.
    </p>

    <div class="idcard">
      <section class="idcard__preview" aria-labelledby="idcard-preview">
        <h3 id="idcard-preview">Vorschau</h3>
        <IdCardPreview
          :values="values"
          :former-member="formerMember"
          :photo="printPhoto ? prepared?.onCardCorrected : undefined"
          :paper="settings.paper"
          :font="settings.font"
        />
        <fieldset class="idcard__choice idcard__fonts">
          <legend>Schrift (fett)</legend>
          <label v-for="(meta, key) in CARD_FONTS" :key="key">
            <input v-model="settings.font" type="radio" :value="key" /> {{ meta.label }}
          </label>
        </fieldset>
      </section>

      <section class="idcard__fields" aria-labelledby="idcard-person">
        <h3 id="idcard-person">Angaben</h3>
        <div class="idcard__grid">
          <label v-for="field in PERSON_FIELDS" :key="field.key" class="idcard__field" :class="{ 'idcard__field--wide': field.wide }">
            <span>{{ field.label }}</span>
            <InputText v-model="values[field.key]" />
          </label>
        </div>

        <h3>War Mitglied der Jugendfeuerwehr</h3>
        <div class="idcard__grid">
          <label class="idcard__field idcard__field--wide">
            <span>Gemeinde/Ort</span>
            <InputText v-model="values.gemeindeOrt" />
          </label>
          <label class="idcard__field">
            <span>vom – bis</span>
            <InputText v-model="values.vonBis" placeholder="z. B. 2019 – 2023" />
          </label>
          <fieldset class="idcard__choice">
            <legend>Ankreuzen</legend>
            <label><input v-model="formerMember" type="radio" :value="true" /> Ja</label>
            <label><input v-model="formerMember" type="radio" :value="false" /> Nein</label>
            <label><input v-model="formerMember" type="radio" :value="null" /> nichts</label>
          </fieldset>
        </div>

        <h3>Ist Mitglied der Jugendfeuerwehr</h3>
        <div class="idcard__grid">
          <label v-for="field in MEMBERSHIP_FIELDS" :key="field.key" class="idcard__field" :class="{ 'idcard__field--wide': field.wide }">
            <span>{{ field.label }}</span>
            <InputText v-model="values[field.key]" />
          </label>
        </div>
      </section>

      <section class="idcard__photo" aria-labelledby="idcard-photo">
        <h3 id="idcard-photo">Passbild</h3>
        <p v-if="photoState === 'loading'" class="idcard__hint">Lade Profilbild …</p>
        <p v-else-if="photoState === 'missing'" class="idcard__hint">Kein Profilbild hinterlegt; das Feld bleibt frei zum Einkleben.</p>
        <template v-else-if="prepared">
          <div class="idcard__previews">
            <figure>
              <img :src="prepared.onCardPlain" alt="Simulation: Passbild ohne Korrektur auf dem gelben Ausweis" />
              <figcaption>Ohne Korrektur</figcaption>
            </figure>
            <figure>
              <img :src="prepared.onCardCorrected" alt="Simulation: Passbild mit Korrektur auf dem gelben Ausweis" />
              <figcaption>Mit Korrektur</figcaption>
            </figure>
          </div>
          <label class="idcard__check"><input v-model="printPhoto" type="checkbox" /> Passbild mitdrucken</label>
          <label class="idcard__field">
            <span>Farbkorrektur {{ Math.round(settings.strength * 100) }} %</span>
            <input v-model.number="settings.strength" type="range" min="0" max="1" step="0.05" />
          </label>
          <label class="idcard__field idcard__field--inline">
            <span>Farbton des Ausweises</span>
            <input v-model="settings.paper" type="color" class="idcard__color" />
          </label>
          <p class="idcard__hint">
            Die Vorschau simuliert den Druck auf dem gelben Karton. Passt der Farbton nicht, halte einen Ausweis neben den
            Bildschirm und gleiche ihn an.
          </p>
        </template>

        <h3>Drucker einstellen</h3>
        <div class="idcard__grid">
          <label class="idcard__field">
            <span>Versatz rechts (mm)</span>
            <InputNumber v-model="settings.offsetX" :min-fraction-digits="0" :max-fraction-digits="1" :step="0.5" show-buttons :min="-15" :max="15" />
          </label>
          <label class="idcard__field">
            <span>Versatz unten (mm)</span>
            <InputNumber v-model="settings.offsetY" :min-fraction-digits="0" :max-fraction-digits="1" :step="0.5" show-buttons :min="-15" :max="15" />
          </label>
        </div>
        <label class="idcard__check"><input v-model="guides" type="checkbox" /> Probedruck mit Hilfslinien (auf Normalpapier)</label>
        <p class="idcard__hint">
          Erst einen Probedruck auf Normalpapier machen, gegen das Licht auf einen Ausweis legen und den Versatz
          anpassen. Die Einstellung bleibt in diesem Browser gespeichert.
        </p>
      </section>
    </div>

    <p v-if="error" class="idcard__error" role="alert">{{ error }}</p>

    <template #footer>
      <Button label="Abbrechen" text severity="secondary" @click="emit('update:visible', false)" />
      <Button label="Als PDF speichern" icon="pi pi-download" severity="secondary" :loading="busy === 'download'" @click="run('download')" />
      <Button :label="guides ? 'Probedruck' : 'Drucken'" icon="pi pi-print" :loading="busy === 'print'" @click="run('print')" />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import { useIdCardPrintSettings } from '@/composables/useIdCardPrintSettings'
import { useDepartmentsStore } from '@/stores/departments'
import type { Member } from '@/types/members'
import { downloadPdf, imageAsDataUrl, printPdf } from '@/utils/admissionPdf'
import IdCardPreview from '@/components/members/molecules/IdCardPreview.vue'
import { CARD_FONTS, PHOTO_ASPECT, buildIdCardPdf, type CardTextField, type CardValues } from '@/utils/djfIdCard'
import { typewriterFont } from '@/utils/pdfFonts'
import { memberDepartmentIds } from '@/utils/extraFields'
import { cropPassport, preparePhoto, type PreparedPhoto } from '@/utils/idCardPhoto'

interface Props {
  visible: boolean
  member: Member
}

const props = defineProps<Props>()
const emit = defineEmits<{ (e: 'update:visible', value: boolean): void }>()

const PERSON_FIELDS: { key: CardTextField; label: string; wide?: boolean }[] = [
  { key: 'vorname', label: 'Vorname' },
  { key: 'name', label: 'Name' },
  { key: 'geburtsdatum', label: 'Geburtsdatum' },
  { key: 'strasse', label: 'Straße' },
  { key: 'plzWohnort', label: 'PLZ/Wohnort', wide: true }
]
const MEMBERSHIP_FIELDS: { key: CardTextField; label: string; wide?: boolean }[] = [
  { key: 'stadtOrt', label: 'Stadt/Ort' },
  { key: 'stadtOrtsteil', label: 'Stadt/Ortsteil' },
  { key: 'seitDem', label: 'seit dem' },
  { key: 'datumUnterschrift', label: 'Datum (neben der Unterschrift)' }
]

const { settings } = useIdCardPrintSettings()
const departments = useDepartmentsStore()
const values = reactive<CardValues>({
  vorname: '',
  name: '',
  geburtsdatum: '',
  strasse: '',
  plzWohnort: '',
  gemeindeOrt: '',
  vonBis: '',
  stadtOrt: '',
  stadtOrtsteil: '',
  seitDem: '',
  datumUnterschrift: ''
})
const formerMember = ref<boolean | null>(null)
const guides = ref(false)
const printPhoto = ref(true)
const cropped = ref<ImageData | null>(null)
const photoState = ref<'loading' | 'missing' | 'ready'>('missing')
const busy = ref<'download' | 'print' | null>(null)
const error = ref('')

const prepared = computed<PreparedPhoto | null>(() =>
  cropped.value ? preparePhoto(cropped.value, settings.paper, settings.strength) : null
)

const formatDate = (iso: string | null | undefined) =>
  iso ? new Date(`${iso}T00:00:00`).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' }) : ''

/** "Musterweg 1, 12345 Musterstadt" → "Musterstadt" */
function cityOf(address: string | undefined) {
  return /\b\d{5}\s+(.+)$/.exec(address ?? '')?.[1]?.trim() ?? ''
}

function prefill(member: Member) {
  const department = departments.departments.find((entry) => memberDepartmentIds(member).includes(entry.id))
  Object.assign(values, {
    vorname: member.name,
    name: member.lastname,
    geburtsdatum: formatDate(member.birthday),
    strasse: member.street ?? '',
    plzWohnort: [member.zip_code, member.city].filter(Boolean).join(' '),
    gemeindeOrt: '',
    vonBis: '',
    stadtOrt: cityOf(department?.address),
    stadtOrtsteil: department?.name ?? '',
    seitDem: formatDate(member.joined),
    datumUnterschrift: formatDate(new Date().toISOString().slice(0, 10))
  })
  formerMember.value = null
  guides.value = false
  error.value = ''
}

async function loadPhoto(member: Member) {
  cropped.value = null
  if (!member.avatar_url) {
    photoState.value = 'missing'
    return
  }
  photoState.value = 'loading'
  try {
    cropped.value = await cropPassport(await imageAsDataUrl(member.avatar_url), PHOTO_ASPECT)
    photoState.value = 'ready'
  } catch {
    photoState.value = 'missing'
  }
}

watch(
  () => props.visible,
  (open) => {
    if (!open) return
    if (!departments.departments.length) departments.fetchDepartments()
    prefill(props.member)
    loadPhoto(props.member)
  },
  { immediate: true }
)

async function run(kind: 'download' | 'print') {
  busy.value = kind
  error.value = ''
  const definition = buildIdCardPdf({
    values: { ...values },
    formerMember: formerMember.value,
    photo: printPhoto.value ? prepared.value?.print : undefined,
    offset: { x: settings.offsetX ?? 0, y: settings.offsetY ?? 0 },
    guides: guides.value,
    title: `DJF-Ausweis ${values.vorname} ${values.name}`,
    font: settings.font
  })
  try {
    const fonts = settings.font === 'typewriter' ? await typewriterFont() : undefined
    if (kind === 'print') await printPdf(definition, fonts)
    else await downloadPdf(definition, `djf-ausweis-${props.member.lastname}-${props.member.name}.pdf`.toLowerCase(), fonts)
  } catch {
    error.value = 'Das PDF konnte nicht erstellt werden.'
  } finally {
    busy.value = null
  }
}
</script>

<style scoped>
.idcard__lead,
.idcard__hint {
  margin: 0 0 var(--jf-space-1-5);
  font-size: var(--jf-text-sm);
  color: var(--jf-color-text-muted);
}

.idcard {
  display: flex;
  flex-wrap: wrap;
  gap: var(--jf-space-3);
}

.idcard__preview {
  flex: 0 1 17rem;
  min-width: 12rem;
  /* The card is tall; keep it in view while the form scrolls. */
  align-self: flex-start;
  position: sticky;
  top: 0;
}

.idcard__fonts {
  margin-top: var(--jf-space-1-5);
}

.idcard__fields {
  flex: 3 1 22rem;
  min-width: 0;
}

.idcard__photo {
  flex: 2 1 16rem;
  min-width: 0;
}

.idcard h3 {
  margin: var(--jf-space-2) 0 var(--jf-space-1);
  font-size: var(--jf-text-md);
}

.idcard h3:first-child {
  margin-top: 0;
}

.idcard__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--jf-space-1-5);
}

.idcard__field {
  display: flex;
  flex-direction: column;
  gap: var(--jf-space-0-5);
  font-size: var(--jf-text-sm);
  min-width: 0;
}

/* PrimeVue number inputs bring a fixed width; let them follow the grid column. */
.idcard__field :deep(.p-inputnumber),
.idcard__field :deep(.p-inputnumber-input),
.idcard__field :deep(.p-inputtext) {
  width: 100%;
  min-width: 0;
}

.idcard__field--wide {
  grid-column: 1 / -1;
}

.idcard__field--inline {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  margin: var(--jf-space-1) 0;
}

.idcard__choice {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--jf-space-1-5);
  margin: 0;
  padding: 0;
  border: 0;
  font-size: var(--jf-text-sm);
}

.idcard__choice legend {
  margin-bottom: var(--jf-space-0-5);
}

.idcard__check {
  display: flex;
  align-items: center;
  gap: var(--jf-space-1);
  min-height: var(--jf-touch-target, 44px);
  font-size: var(--jf-text-sm);
}

.idcard__color {
  width: 3rem;
  height: 2rem;
  border: 1px solid var(--jf-color-border);
  border-radius: var(--jf-radius-sm);
  background: none;
}

.idcard__previews {
  display: flex;
  gap: var(--jf-space-1-5);
}

.idcard__previews figure {
  margin: 0;
  flex: 1;
  text-align: center;
  font-size: var(--jf-text-xs);
  color: var(--jf-color-text-muted);
}

.idcard__previews img {
  width: 100%;
  max-width: 9rem;
  aspect-ratio: 35 / 45;
  object-fit: cover;
  border: 1px solid var(--jf-color-border);
}

.idcard__error {
  margin: var(--jf-space-1) 0 0;
  color: var(--jf-color-danger);
}

@media (max-width: 640px) {
  .idcard__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
