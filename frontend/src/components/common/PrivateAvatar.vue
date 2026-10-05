<template><Avatar v-bind="$attrs" :image="resolved" /></template>
<script setup lang="ts">
import { toRef } from 'vue'
import Avatar from 'primevue/avatar'
import { usePrivateMedia } from '@/composables/usePrivateMedia'
defineOptions({ inheritAttrs: false })
const props = defineProps<{ image?: string | null }>()
const resolved = usePrivateMedia(toRef(props, 'image'))
</script>
