<template><Image v-bind="$attrs" :src="resolved" /></template>
<script setup lang="ts">
import { toRef } from 'vue'
import Image from 'primevue/image'
import { usePrivateMedia } from '@/composables/usePrivateMedia'
defineOptions({ inheritAttrs: false })
const props = defineProps<{ src?: string | null }>()
const resolved = usePrivateMedia(toRef(props, 'src'))
</script>
