<template>
  <Tag :value="label" :icon="icon" :severity="severity" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Tag from 'primevue/tag'

interface Props {
  isMember: boolean
}

const props = defineProps<Props>()

const label = computed(() => (props.isMember ? 'Mitglied' : 'Lager'))
const icon = computed(() => (props.isMember ? 'pi pi-user' : 'pi pi-box'))
const severity = computed(() => (props.isMember ? 'info' : 'secondary'))
</script>
