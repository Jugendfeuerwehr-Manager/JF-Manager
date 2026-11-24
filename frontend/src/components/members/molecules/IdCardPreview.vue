<template>
  <svg
    class="card"
    :viewBox="`0 0 ${CARD_WIDTH} ${CARD_HEIGHT}`"
    role="img"
    :aria-label="`Vorschau des DJF-Ausweises für ${values.vorname} ${values.name}`"
  >
    <!-- Card stock and the pre-printed frame (mock-up, drawn from the template measurements). -->
    <rect x="0" y="0" :width="CARD_WIDTH" :height="CARD_HEIGHT" :fill="paper" />
    <g class="card__print">
      <rect x="23.8" y="31.7" width="253.4" height="171.3" fill="none" stroke-width="0.8" />
      <line x1="219.6" y1="31.7" x2="219.6" y2="203" stroke-width="0.6" />
      <text x="34.6" y="66" class="card__title">MITGLIEDS<tspan font-weight="700">AUSWEIS</tspan></text>
      <text x="34.6" y="91" class="card__sub">DER DEUTSCHEN <tspan font-weight="700">JUGEND</tspan>FEUERWEHR</text>
      <text x="34.6" y="101.5" class="card__sub">IM DEUTSCHEN <tspan font-weight="700">FEUERWEHR</tspan>VERBAND e.V.</text>
      <g class="card__logo" aria-hidden="true">
        <path d="M248 50 C236 66 236 82 244 92 C238 80 246 70 252 64 C252 76 260 82 262 92 C270 80 266 62 248 50 Z" />
        <circle cx="249" cy="104" r="13" />
      </g>
      <text x="11" y="420" class="card__side" transform="rotate(-90 11 420)">
        Dieser Ausweis bleibt, auch nach Austritt, im Besitz des Ausweisinhabers/in.
      </text>

      <template v-for="line in LINES" :key="line.label">
        <line :x1="line.x1" :y1="line.y" :x2="line.x2" :y2="line.y" stroke-width="0.6" />
        <text :x="line.x1" :y="line.y + 9" class="card__label">{{ line.label }}</text>
      </template>
      <text x="23.6" y="355" class="card__label">Der/die Inhaber/in dieses Ausweises war Mitglied der Jugendfeuerwehr:</text>
      <text x="61" y="421.7" class="card__label">bis</text>
      <rect v-for="box in [CARD_FIELDS.ja, CARD_FIELDS.nein]" :key="box.x" :x="box.x" :y="box.y" :width="box.w" :height="box.h" fill="none" stroke-width="0.6" />
      <text :x="CARD_FIELDS.ja.x + 2" y="421.7" class="card__label">Ja</text>
      <text :x="CARD_FIELDS.nein.x" y="421.7" class="card__label">Nein (Zutreffendes bitte ankreuzen)</text>
      <text x="23.6" y="458" class="card__label">Der/die Inhaber/in dieses Mitgliedsausweises ist Mitglied der Jugendfeuer-</text>
      <text x="23.6" y="467" class="card__label">wehr der Freiwilligen Feuerwehr</text>
      <circle cx="56" cy="617" r="29" fill="none" stroke-width="0.6" />
      <text x="56" y="619" class="card__label" text-anchor="middle">Siegel</text>
      <rect :x="PHOTO_FRAME.x" :y="PHOTO_FRAME.y" :width="PHOTO_FRAME.w" :height="PHOTO_FRAME.h" fill="none" stroke-width="0.6" />
      <line x1="144" y1="751" x2="282" y2="751" stroke-width="0.6" />
      <text x="144" y="760" class="card__label">Unterschrift des/der Inhabers/Inhaberin</text>
    </g>

    <!-- What the printer adds. -->
    <image
      v-if="photo"
      :href="photo"
      :x="PHOTO.x"
      :y="PHOTO.y"
      :width="PHOTO.w"
      :height="PHOTO.h"
      preserveAspectRatio="xMidYMid slice"
    />
    <g class="card__print">
      <circle cx="124" cy="819" r="29" :fill="paper" stroke-width="0.6" />
      <text x="124" y="821" class="card__label" text-anchor="middle">Siegel</text>
    </g>
    <g class="card__values" :class="`card__values--${font}`">
      <text
        v-for="entry in placed"
        :key="entry.key"
        :x="entry.x"
        :y="entry.y + entry.fontSize * 0.9"
        :font-size="entry.fontSize"
      >{{ entry.text }}</text>
      <g v-if="formerMember !== null" :transform="`translate(${cross.x} ${cross.y})`" class="card__cross">
        <line x1="1.5" y1="1.5" :x2="cross.w - 1.5" :y2="cross.h - 1.5" />
        <line :x1="cross.w - 1.5" y1="1.5" x2="1.5" :y2="cross.h - 1.5" />
      </g>
    </g>
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  CARD_FIELDS,
  CARD_HEIGHT,
  CARD_WIDTH,
  PHOTO,
  PHOTO_FRAME,
  valuePlacement,
  type CardFont,
  type CardTextField,
  type CardValues
} from '@/utils/djfIdCard'

interface Props {
  values: CardValues
  formerMember: boolean | null
  /** passport photo as it would look printed on the card */
  photo?: string
  /** card stock colour */
  paper: string
  font: CardFont
}

const props = defineProps<Props>()

const underline = (box: { x: number; y: number; w: number; h: number }, label: string) => ({
  x1: box.x,
  x2: box.x + box.w,
  y: box.y + box.h,
  label
})

// Printed rules sit at the lower edge of the template's form fields.
const LINES = [
  underline(CARD_FIELDS.vorname, 'Vorname'),
  underline(CARD_FIELDS.name, 'Name'),
  underline(CARD_FIELDS.geburtsdatum, 'Geburtsdatum'),
  underline(CARD_FIELDS.strasse, 'Straße'),
  underline(CARD_FIELDS.plzWohnort, 'PLZ/Wohnort'),
  underline(CARD_FIELDS.gemeindeOrt, 'Gemeinde/Ort'),
  underline(CARD_FIELDS.vonBis, 'vom'),
  underline(CARD_FIELDS.stadtOrt, 'Stadt/Ort'),
  underline(CARD_FIELDS.stadtOrtsteil, 'Stadt/Ortsteil'),
  underline(CARD_FIELDS.seitDem, 'seit dem'),
  { ...underline(CARD_FIELDS.datumUnterschrift, 'Datum/Unterschrift'), x2: 277 }
]

const placed = computed(() =>
  (Object.keys(CARD_FIELDS) as (keyof typeof CARD_FIELDS)[])
    .filter((key): key is CardTextField => key !== 'ja' && key !== 'nein')
    .map((key) => ({ key, text: props.values[key].trim(), box: CARD_FIELDS[key] }))
    .filter((entry) => entry.text)
    .map((entry) => ({ key: entry.key, text: entry.text, ...valuePlacement(entry.box, entry.text, props.font) }))
)
const cross = computed(() => (props.formerMember ? CARD_FIELDS.ja : CARD_FIELDS.nein))
</script>

<style scoped>
@font-face {
  font-family: 'JF Courier Prime';
  font-weight: 700;
  src: url('@/assets/fonts/courier-prime/CourierPrime-Bold.ttf') format('truetype');
}

/* A paper mock-up: black print on card stock in every theme. */
.card {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 2px;
  box-shadow: var(--jf-shadow-md);
  font-family: Roboto, Arial, sans-serif;
}

.card__print {
  stroke: black;
  fill: black;
}

.card__print text {
  stroke: none;
}

.card__title {
  font-size: 15px;
  letter-spacing: 0.2px;
}

.card__sub {
  font-size: 6.4px;
  letter-spacing: 0.3px;
}

.card__label {
  font-size: 5.6px;
}

.card__side {
  font-size: 4.6px;
}

.card__logo path {
  fill: red;
  stroke: none;
}

.card__logo circle {
  fill: gold;
  stroke: darkred;
  stroke-width: 1.5;
}

.card__values text {
  fill: black;
  font-weight: 700;
}

.card__values--typewriter text {
  font-family: 'JF Courier Prime', 'Courier New', monospace;
}

.card__values--clear text {
  font-family: Roboto, Arial, sans-serif;
}

.card__cross line {
  stroke: black;
  stroke-width: 1.2;
}
</style>
