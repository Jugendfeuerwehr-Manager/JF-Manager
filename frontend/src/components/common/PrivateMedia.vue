<template>
  <iframe v-if="pdf" :src="resolved" sandbox="" referrerpolicy="no-referrer" title="Dateivorschau" />
  <img v-else :src="resolved" referrerpolicy="no-referrer" />
</template>
<script setup lang="ts">
import { toRef } from 'vue'
import { usePrivateMedia } from '@/composables/usePrivateMedia'
const props = defineProps<{ src?: string | null; pdf?: boolean }>()
const resolved = usePrivateMedia(toRef(props, 'src'), props.pdf)
</script>
