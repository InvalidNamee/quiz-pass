<script setup lang="ts">
import { computed } from 'vue'
import { renderMathTextToHtml } from '../utils/mathjax'

const props = withDefaults(defineProps<{
  text: string | null | undefined
  as?: string
}>(), {
  as: 'span',
})

const renderedHtml = computed(() => renderMathTextToHtml(props.text || ''))
</script>

<template>
  <component :is="as" class="whitespace-pre-wrap" v-html="renderedHtml" />
</template>
