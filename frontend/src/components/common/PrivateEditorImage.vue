<template>
  <NodeViewWrapper as="span" class="editor-image">
    <PrivateMedia :src="node.attrs.src" :alt="node.attrs.alt" :title="node.attrs.title" />
  </NodeViewWrapper>
</template>
<script setup lang="ts">
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
import PrivateMedia from './PrivateMedia.vue'
defineProps(nodeViewProps)
</script>
