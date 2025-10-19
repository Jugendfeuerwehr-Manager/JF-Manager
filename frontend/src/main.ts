import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import ConfirmationService from 'primevue/confirmationservice'
import ToastService from 'primevue/toastservice'
import Tooltip from 'primevue/tooltip'

import App from './App.vue'
import router from './router'

import 'primeicons/primeicons.css'
import './assets/styles.css'

// Import German locale for PrimeVue
const deLocale = {
  startsWith: 'Beginnt mit',
  contains: 'Enthält',
  notContains: 'Enthält nicht',
  endsWith: 'Endet mit',
  equals: 'Gleich',
  notEquals: 'Ungleich',
  noFilter: 'Kein Filter',
  filter: 'Filter',
  lt: 'Kleiner als',
  lte: 'Kleiner oder gleich',
  gt: 'Größer als',
  gte: 'Größer oder gleich',
  dateIs: 'Datum ist',
  dateIsNot: 'Datum ist nicht',
  dateBefore: 'Datum ist vor',
  dateAfter: 'Datum ist nach',
  custom: 'Benutzerdefiniert',
  clear: 'Löschen',
  apply: 'Anwenden',
  matchAll: 'Alle erfüllen',
  matchAny: 'Mindestens eines erfüllt',
  addRule: 'Regel hinzufügen',
  removeRule: 'Regel entfernen',
  accept: 'Ja',
  reject: 'Nein',
  choose: 'Auswählen',
  upload: 'Hochladen',
  cancel: 'Abbrechen',
  completed: 'Abgeschlossen',
  pending: 'Ausstehend',
  dayNames: ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'],
  dayNamesShort: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
  dayNamesMin: ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
  monthNames: ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'],
  monthNamesShort: ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez'],
  chooseYear: 'Jahr wählen',
  chooseMonth: 'Monat wählen',
  chooseDate: 'Datum wählen',
  prevDecade: 'Vorheriges Jahrzehnt',
  nextDecade: 'Nächstes Jahrzehnt',
  prevYear: 'Vorheriges Jahr',
  nextYear: 'Nächstes Jahr',
  prevMonth: 'Vorheriger Monat',
  nextMonth: 'Nächster Monat',
  prevHour: 'Vorherige Stunde',
  nextHour: 'Nächste Stunde',
  prevMinute: 'Vorherige Minute',
  nextMinute: 'Nächste Minute',
  prevSecond: 'Vorherige Sekunde',
  nextSecond: 'Nächste Sekunde',
  am: 'AM',
  pm: 'PM',
  today: 'Heute',
  weekHeader: 'KW',
  firstDayOfWeek: 1,
  showMonthAfterYear: false,
  dateFormat: 'dd.mm.yy',
  weak: 'Schwach',
  medium: 'Mittel',
  strong: 'Stark',
  passwordPrompt: 'Passwort eingeben',
  emptyFilterMessage: 'Keine Ergebnisse gefunden',
  searchMessage: '{0} Ergebnisse verfügbar',
  selectionMessage: '{0} Einträge ausgewählt',
  emptySelectionMessage: 'Kein Eintrag ausgewählt',
  emptySearchMessage: 'Keine Ergebnisse gefunden',
  emptyMessage: 'Keine Einträge verfügbar',
  aria: {
    trueLabel: 'Wahr',
    falseLabel: 'Falsch',
    nullLabel: 'Nicht ausgewählt',
    star: '1 Stern',
    stars: '{star} Sterne',
    selectAll: 'Alle Einträge ausgewählt',
    unselectAll: 'Alle Einträge abgewählt',
    close: 'Schließen',
    previous: 'Zurück',
    next: 'Weiter',
    navigation: 'Navigation',
    scrollTop: 'Nach oben scrollen',
    moveTop: 'An den Anfang',
    moveUp: 'Nach oben',
    moveDown: 'Nach unten',
    moveBottom: 'An das Ende',
    moveToTarget: 'Zum Ziel',
    moveToSource: 'Zur Quelle',
    moveAllToTarget: 'Alles zum Ziel',
    moveAllToSource: 'Alles zur Quelle',
    pageLabel: 'Seite {page}',
    firstPageLabel: 'Erste Seite',
    lastPageLabel: 'Letzte Seite',
    nextPageLabel: 'Nächste Seite',
    prevPageLabel: 'Vorherige Seite',
    rowsPerPageLabel: 'Zeilen pro Seite',
    jumpToPageDropdownLabel: 'Zu Seite springen',
    jumpToPageInputLabel: 'Zu Seite springen',
    selectRow: 'Zeile ausgewählt',
    unselectRow: 'Zeile abgewählt',
    expandRow: 'Zeile aufgeklappt',
    collapseRow: 'Zeile zugeklappt',
    showFilterMenu: 'Filtermenü anzeigen',
    hideFilterMenu: 'Filtermenü verbergen',
    filterOperator: 'Filteroperator',
    filterConstraint: 'Filtereinschränkung',
    editRow: 'Zeile bearbeiten',
    saveEdit: 'Bearbeitung speichern',
    cancelEdit: 'Bearbeitung abbrechen',
    listView: 'Listenansicht',
    gridView: 'Gitteransicht',
    slide: 'Folie',
    slideNumber: '{slideNumber}',
    zoomImage: 'Bild vergrößern',
    zoomIn: 'Vergrößern',
    zoomOut: 'Verkleinern',
    rotateRight: 'Nach rechts drehen',
    rotateLeft: 'Nach links drehen'
  }
}

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: 'system',
      cssLayer: false
    }
  },
  locale: deLocale
})
app.use(ConfirmationService)
app.use(ToastService)
app.directive('tooltip', Tooltip)


// Initialize auth store
import { useAuthStore } from './stores/auth'
const authStore = useAuthStore()
authStore.initialize()

app.mount('#app')
