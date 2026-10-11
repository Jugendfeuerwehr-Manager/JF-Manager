<template>
  <svg
    class="brand-mark"
    :width="size"
    :height="size"
    viewBox="0 0 120 120"
    aria-hidden="true"
    focusable="false"
  >
    <rect width="120" height="120" rx="30" class="brand-mark__ground" />
    <g transform="translate(14 10) scale(0.78)" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="M46 20 V66 C46 80 38 88 28 88 C22 88 18 85 16 82" class="brand-mark__light" stroke-width="14" />
      <path d="M70 74 V20 H98 M70 46 H92" class="brand-mark__accent" stroke-width="14" />
      <path d="M14 106 C46 114 84 110 108 90" class="brand-mark__light" stroke-width="6" />
    </g>
  </svg>
</template>

<script setup lang="ts">
interface Props {
  size?: number
}

withDefaults(defineProps<Props>(), { size: 36 })
</script>

<style scoped>
.brand-mark {
  display: block;
  flex-shrink: 0;
}

.brand-mark__ground {
  fill: var(--jf-logo-blue);
}

.brand-mark__light {
  stroke: var(--jf-logo-light);
}

.brand-mark__accent {
  stroke: var(--jf-logo-orange);
}
</style>
